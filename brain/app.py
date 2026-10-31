"""The brain: one FastAPI app every module talks to (Aaron, Module B).
Run:  uvicorn brain.app:app --host 0.0.0.0 --port 8000
"""
import asyncio, hmac, time
from datetime import datetime, timezone
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from common.config import CLINIC_DOMAIN, DEVICE_ID, OWNER_CHAT_ID, AGENT_TOKEN
from brain import graph as G
from brain.scoring import score_filter
from brain.audit import AuditLog
from brain.correlate import Incidents

app = FastAPI(title="Chakravyuh brain")

try:                                       # Bruce's honeytoken links: GET /t/<token>
    from sensors.honeytoken import router as honey_router
    app.include_router(honey_router)
except Exception as e:
    print("Honeytoken routes not loaded:", e)
graph = G.build_demo_graph()
audit = AuditLog()
incidents = Incidents()
last_heartbeat = {}            # device -> unix time
agent_commands = {}            # device -> list of commands waiting for the agent
recent_changes = []            # unix times of risky changes (forwarding added etc.)
notifier = None                # set by Sahayak: a function(incident_dict) that sends the alert
last_sent = {}                 # alert key -> unix time it was last sent to the phones
RESEND_AFTER = 600             # the same alert again within 10 min is audited but not re-sent

def alert_key(e):
    """Same signal type on the same thing. A new filter or file is a new alert (it needs its own button)."""
    ev = e.evidence or {}
    return (e.type, e.entity, (ev.get("filter") or {}).get("id") or ev.get("file_id") or "")

def notify(inc, key=None):
    if key is not None:
        if time.time() - last_sent.get(key, 0) < RESEND_AFTER:
            audit.append({"kind": "notify_skipped", "incident_id": inc["id"], "reason": "same alert sent < 10 min ago"})
            return
        last_sent[key] = time.time()
    if notifier:
        try:
            sent = notifier(incidents.public(inc))
            if sent:                       # who actually received it: checked by eval/check_session4.py
                audit.append({"kind": "notify", "incident_id": inc["id"], "sent": sent})
        except Exception as e:            # never let a Telegram problem break detection
            audit.append({"kind": "notify_error", "error": str(e)})

class Event(BaseModel):
    source: str
    type: str
    entity: str
    evidence: dict = {}
    ts: str = ""

class Action(BaseModel):
    incident_id: int
    action: str            # remove_filter | make_private | contain_pc | release_pc | ack | step_done
    by: str = ""           # chat id of the person who tapped
    step: str = ""

class Heartbeat(BaseModel):
    device: str

def _check_agent(token, what):
    """STRIDE spoofing: when AGENT_TOKEN is set, only the real agent may report, heartbeat or fetch commands."""
    if AGENT_TOKEN and not hmac.compare_digest((token or "").encode(), AGENT_TOKEN.encode()):
        audit.append({"kind": "rejected_agent", "what": what})
        raise HTTPException(401, "unknown agent")

def _recent_change(seconds=24 * 3600):
    cutoff = time.time() - seconds
    return any(t >= cutoff for t in recent_changes)

def _remove_filters(inc):
    """Delete every attacker filter in the incident (Bruce's delete_filter), then turn the Gmail paths grey."""
    from sensors.fixes import delete_filter              # Bruce's module
    removed = None
    for s in inc["signals"]:
        f = s["evidence"].get("filter")
        if f:
            removed = delete_filter(f, audit)
    G.clear_live(graph, "attacker", "gmail"); G.clear_live(graph, "gmail", "invoices")
    return removed

@app.post("/events")
def events_route(e: Event, x_agent_token: str = Header(default="")):
    if e.source == "agent":
        _check_agent(x_agent_token, "event:" + e.type)
    return post_event(e)

def post_event(e: Event):
    """Also called directly by the heartbeat watcher and the honeytoken route (no token needed inside)."""
    ev = e.model_dump()
    audit.append({"kind": "event", **ev})
    sig = {"type": e.type, "entity": e.entity, "evidence": e.evidence}
    inc, title, severity, policy, merge = None, None, None, "tap", True

    if e.type == "filter_added":
        s = score_filter(e.evidence.get("filter", {}), CLINIC_DOMAIN, _recent_change())
        sig["score"] = s
        if s["level"] == "digest":
            return {"ok": True, "level": "digest", "score": s}
        severity = "high" if s["level"] == "alert" else "medium"
        title = "A hidden email rule may be sending your mail to a stranger"
        G.mark_live(graph, "attacker", "gmail"); G.mark_live(graph, "gmail", "invoices")
    elif e.type == "forwarding_added":
        recent_changes.append(time.time())
        severity, title = "medium", "Someone is trying to copy your email to a stranger"
        G.mark_live(graph, "attacker", "gmail")
    elif e.type in ("autoforward_on", "sendas_added"):
        recent_changes.append(time.time())
        severity, title = "high", "Your email settings were changed to send mail elsewhere"
        G.mark_live(graph, "attacker", "gmail")
    elif e.type == "file_public":
        severity, title = "high", "A private folder can now be opened by anyone"
        G.mark_live(graph, "attacker", "drive", "public_link_live")
    elif e.type == "honeytoken_hit":
        severity, title = "high", "A stranger opened the fake bank login we hid in your files"
        if "email" in e.evidence.get("planted_in", ""):    # decoy email: they are in the mailbox
            G.mark_live(graph, "attacker", "gmail")
        else:                                             # decoy doc lives in Drive: attacker -> records path
            G.mark_live(graph, "attacker", "drive", "decoy_opened")
    elif e.type == "ransomware_suspected":
        severity, title, policy = "critical", "Your front-desk computer started locking files", "auto"
        G.mark_live(graph, "attacker", "pc"); G.mark_live(graph, "pc", "records")
    elif e.type == "heartbeat_missing":
        severity, title = "high", "The protection on the front-desk PC stopped responding"
    elif e.type == "agent_stopping":                     # tamper alarm: the agent was stopped on purpose
        severity, title = "high", "The protection on the front-desk PC was switched off"
        last_heartbeat.pop(e.entity.split(":", 1)[-1], None)   # already alerted: no second heartbeat alert
    elif e.type == "backup_old":
        severity, title, merge = "low", "The clinic's newest backup is old", False
    elif e.type == "files_restored":                     # the agent finished a restore: logged, no new alert
        return {"ok": True, "recorded": e.type}
    elif e.type == "bank_change_request":
        severity, title = "high", "A vendor's bank details changed - pause payment"
    else:
        return {"ok": True, "ignored": e.type}

    inc, merged = incidents.add_signal(sig, severity, title, policy, merge=merge)
    if e.type == "ransomware_suspected" and "contain_pc" not in inc["done"]:
        inc["done"].append("contain_pc")                 # the agent already contained the PC locally
    if "save_evidence" in inc["runbook"] and "save_evidence" not in inc["done"]:
        inc["done"].append("save_evidence")              # the event with its full evidence was just written to the audit log
    audit.append({"kind": "incident", "id": inc["id"], "merged": merged, "severity": inc["severity"]})
    notify(inc, alert_key(e))      # an email+PC merge has a new key, so it is always sent
    return {"ok": True, "incident": incidents.public(inc), "merged": merged}

@app.post("/actions")
def post_action(a: Action):
    inc = incidents.items.get(a.incident_id)
    if not inc:
        raise HTTPException(404, "no such incident")
    audit.append({"kind": "action", **a.model_dump()})
    result = {"ok": True}
    if a.action == "remove_filter":
        result["removed"] = _remove_filters(inc)
    elif a.action == "make_private":
        from sensors.fixes import make_private
        for s in inc["signals"]:
            if s["evidence"].get("file_id"):
                result["made_private"] = make_private(s["evidence"]["file_id"], audit)
        G.clear_live(graph, "attacker", "drive")
        G.apply_fix(graph, "make_private")
    elif a.action in ("contain_pc", "release_pc", "restore_files"):
        if a.action != "contain_pc" and OWNER_CHAT_ID and a.by != OWNER_CHAT_ID:
            raise HTTPException(403, "only the owner can do this")
        agent_commands.setdefault(DEVICE_ID, []).append(a.action.split("_")[0])   # contain | release | restore
        result["queued"] = True
        if a.action == "release_pc":
            G.clear_live(graph, "attacker", "pc"); G.clear_live(graph, "pc", "records")
    elif a.action == "step_done" and a.step:
        if a.step == "remove_attacker_rules" and a.step not in inc["done"]:
            result["removed"] = _remove_filters(inc)     # merged-incident view has no separate "Remove it" button
        if a.step not in inc["done"]:
            inc["done"].append(a.step)
        if a.step == "change_password_from_clean_device" or a.step == "change_password":
            G.apply_fix(graph, "enable_2sv")
        if set(inc["runbook"]) <= set(inc["done"]):
            inc["status"] = "closed"
        notify(inc)                                      # Sahayak sends the next step's button
    return result

@app.post("/heartbeat")
def heartbeat(h: Heartbeat, x_agent_token: str = Header(default="")):
    _check_agent(x_agent_token, "heartbeat")
    last_heartbeat[h.device] = time.time()
    return {"ok": True}

@app.get("/agent/commands")
def commands(device: str, x_agent_token: str = Header(default="")):
    _check_agent(x_agent_token, "commands")
    cmds = agent_commands.pop(device, [])
    return {"commands": cmds}

@app.get("/incidents")
def list_incidents():
    return [incidents.public(i) for i in incidents.items.values()]

def _techniques():
    try:                                   # one MITRE map for the bot and the console: sahayak/ask.py
        from sahayak.ask import TECHNIQUE
        return TECHNIQUE
    except Exception:
        return {}

@app.get("/mitre")
def mitre():
    return _techniques()

@app.get("/incidents/{iid}/report")
def report(iid: int):
    """Expert view: the incident, its MITRE techniques and its audit trail. Contains attacker-written
    evidence, so it is for people only: never feed it to sahayak/ask.py or the AI."""
    inc = incidents.items.get(iid)
    if not inc:
        raise HTTPException(404, "no such incident")
    pub, tech = incidents.public(inc), _techniques()
    ents = set(pub["entities"])
    mine = lambda b: b.get("incident_id") == iid or (b.get("kind") == "incident" and b.get("id") == iid) \
        or (b.get("kind") == "event" and b.get("entity") in ents)
    trail = [r for r in reversed(audit.rows(limit=10000)) if mine(r["body"])]   # oldest first
    return {"incident": pub, "techniques": sorted({tech[s["type"]] for s in inc["signals"] if s["type"] in tech}),
            "audit_trail": trail, "audit_verify": audit.verify()}

@app.get("/graph")
def get_graph():
    return G.to_json(graph)

@app.get("/paths")
def get_paths():
    return [{**p, "sentence": G.path_sentence(p)} for p in G.paths(graph)]

@app.get("/audit")
def get_audit():
    return {"verify": audit.verify(), "rows": audit.rows()}

@app.get("/audit/verify")
def verify():
    return audit.verify()

@app.get("/console")
def console():
    return FileResponse("brain/console/index.html")

async def watch_heartbeats():
    """If an agent that was alive goes quiet for 15 s, treat it as hostile."""
    alerted = set()
    while True:
        await asyncio.sleep(5)
        for dev, t in list(last_heartbeat.items()):
            if time.time() - t > 15 and dev not in alerted:
                alerted.add(dev)
                post_event(Event(source="brain", type="heartbeat_missing", entity=f"device:{dev}",
                                 evidence={"last_seen_seconds_ago": round(time.time() - t)}))
            elif time.time() - t <= 15:
                alerted.discard(dev)

@app.on_event("startup")
async def start():
    asyncio.create_task(watch_heartbeats())
    try:                                   # Sahayak plugs in its sender if Telegram is configured
        from sahayak.notify import send_incident
        global notifier
        notifier = send_incident
    except Exception as e:
        print("Sahayak notifier not loaded:", e)
