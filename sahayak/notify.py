"""Send an incident to staff and owner with signed buttons (Aradhya, Module D).
The brain calls send_incident(incident) whenever an incident opens, merges or a runbook step is done.
It runs inside the brain process, so it never raises and never blocks for long."""
import requests
from common.config import TELEGRAM_TOKEN, OWNER_CHAT_ID, STAFF_CHAT_IDS, SECURITY_CODE, CHAT_LANGS
from sahayak import signing
from sahayak.messages import template_for, STEP_LABEL, STEP_TEXT, STEP_DONE, OWNER_STEPS
from sahayak.llm import reword

LANG = CHAT_LANGS   # chat_id -> "en" | "hi" | "kn"  (from CHAT_LANGS in .env)

BUTTONS = {          # signal type -> [(label, code)]; codes are decoded by the bot
    "filter_added": [("Remove it", "rm"), ("Call my IT helper", "it"), ("What does this mean?", "why")],
    "forwarding_added": [("Show me how", "how"), ("Call my IT helper", "it")],
    "autoforward_on": [("Show me how", "how"), ("Call my IT helper", "it")],
    "sendas_added": [("Show me how", "how"), ("Call my IT helper", "it")],
    "file_public": [("Make it private", "mp"), ("Call my IT helper", "it")],
    "honeytoken_hit": [("Start the fix", "st"), ("Call my IT helper", "it"), ("What does this mean?", "why")],
    "ransomware_suspected": [("Okay, I won't switch it off", "ack"), ("Call my IT helper", "it")],
    "heartbeat_missing": [("Call my IT helper", "it"), ("Show me how", "how")],
    "agent_stopping": [("Call my IT helper", "it"), ("Show me how", "how"), ("What does this mean?", "why")],
    "backup_old": [("Show me how", "how"), ("What does this mean?", "why")],
    "bank_change_request": [("Check with the vendor", "vv"), ("What does this mean?", "why")],
    "unknown": [("Call my IT helper", "it")],
}


def header():
    return f"Sahayak · Code {SECURITY_CODE}"


def incident_type(inc):
    if len(set(inc.get("kinds", []))) > 1:
        return "merged"
    sigs = inc.get("signals") or [{}]
    return sigs[-1].get("type", "unknown")


def base_body(inc, lang="en"):
    """The template for this incident; English may be reworded by the AI."""
    body = template_for(incident_type(inc), lang)
    if lang == "en":
        body = reword(body, {"title": inc.get("title", ""), "severity": inc.get("severity", "")})
    return body


def render(inc, lang="en", body=None):
    """Returns (text, stype). `body` lets send_incident reuse one AI rewording for every English chat."""
    stype = incident_type(inc)
    if body is None:
        body = base_body(inc, lang)
    if stype == "merged":
        done = inc.get("done", [])
        ticks = [f"✔ {STEP_DONE.get(s, s)}" for s in inc.get("runbook", []) if s in done]
        if ticks:
            body += "\n\n" + "\n".join(ticks)
        if inc.get("runbook") and set(inc["runbook"]) <= set(done):
            body += "\n\nAll steps done. Thank you, the clinic is safe again."
    return f"{header()}\n{body}", stype


def buttons_for(inc, stype, is_owner):
    iid = inc["id"]
    if stype == "merged":                          # one runbook step at a time
        runbook, done = inc.get("runbook", []), inc.get("done", [])
        todo = [s for s in runbook if s not in done]
        out = []
        if todo and (todo[0] not in OWNER_STEPS or is_owner):
            label = STEP_LABEL.get(todo[0], STEP_TEXT.get(todo[0], todo[0]))[:40]
            out += [(f"Done: {label}", f"sd{runbook.index(todo[0])}"), ("Show me how", "how")]
        elif todo:                                 # staff wait while the owner confirms
            out.append(("Show me how", "how"))
        if is_owner and "contain_pc" in runbook:
            out.append(("Owner: release the PC", "rel"))
    else:
        out = list(BUTTONS.get(stype, BUTTONS["unknown"]))
        if is_owner and stype == "ransomware_suspected":
            out.append(("Owner: release the PC", "rel"))
    return [(label, signing.make(iid, code)) for label, code in out]


def keyboard(buttons):
    return {"inline_keyboard": [[{"text": label, "callback_data": data}] for label, data in buttons]}


def _send(chat_id, text, buttons):
    r = requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                      json={"chat_id": chat_id, "text": text, "reply_markup": keyboard(buttons)}, timeout=10)
    if not r.ok:
        print(f"[Sahayak] Telegram refused the message to {chat_id}: {r.status_code} {r.text[:200]}")


def send_incident(inc):
    chats = [c for c in [OWNER_CHAT_ID] + STAFF_CHAT_IDS if c]
    english = None                                 # reword once, not once per phone
    for chat in chats or ["(no OWNER_CHAT_ID / STAFF_CHAT_IDS in .env)"]:
        lang = LANG.get(chat, "en")
        if lang == "en" and english is None:
            english = base_body(inc, "en")
        text, stype = render(inc, lang, body=english if lang == "en" else None)
        buttons = buttons_for(inc, stype, chat == OWNER_CHAT_ID)
        if not TELEGRAM_TOKEN or not chats:
            print(f"[Sahayak] would send to {chat}:\n{text}\n  buttons: {[b[0] for b in buttons]}\n")
            continue
        try:                                       # one phone failing must not stop the others
            _send(chat, text, buttons)
            if lang in ("kn", "hi"):
                from sahayak.voice import send_voice_later
                send_voice_later(chat, text.split("\n", 1)[1].split("\n\n", 1)[0], lang)  # skip code line and ticks
        except Exception as e:
            print(f"[Sahayak] could not send to {chat}: {e}")
