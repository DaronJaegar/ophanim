"""Golden-path wiring in the brain:  python -m pytest tests -q"""
import sys, types
import pytest
from fastapi.testclient import TestClient
from brain import app as A, graph as G
from brain.audit import AuditLog
from brain.correlate import Incidents

FILTER = {"id": "f1", "criteria": {"query": "invoice OR payment"}, "action": {"forward": "x@evil.com"}}

@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(A, "audit", AuditLog(":memory:"))
    monkeypatch.setattr(A, "incidents", Incidents())
    monkeypatch.setattr(A, "graph", G.build_demo_graph())
    monkeypatch.setattr(A, "notifier", None)
    monkeypatch.setattr(A, "BRAIN_TOKEN", "")             # independent of the token in .env
    monkeypatch.setattr(A, "last_sent", {})
    for name in ("alerted_at", "reminded"):
        monkeypatch.setattr(A, name, {})
    monkeypatch.setattr(A, "acted", set())
    monkeypatch.setattr(A, "recent_changes", [])           # F5: one test's risky rule must not boost the next test
    monkeypatch.setattr(A, "confirmed_filters", set())
    monkeypatch.setattr(A, "digest", [])
    deleted = []
    fake = types.ModuleType("sensors.fixes")
    fake.delete_filter = lambda f, audit: deleted.append(f["id"]) or True
    monkeypatch.setitem(sys.modules, "sensors.fixes", fake)
    c = TestClient(A.app)
    c.deleted = deleted
    return c

def _event(c, type_, entity, evidence=None):
    return c.post("/events", json={"source": "t", "type": type_, "entity": entity, "evidence": evidence or {}}).json()

def test_merged_remove_step_deletes_filter_and_greys_paths(client):
    inc = _event(client, "filter_added", "gmail:clinic", {"filter": FILTER})["incident"]
    _event(client, "ransomware_suspected", "device:frontdesk-pc")
    assert any(e["data"]["live"] for e in client.get("/graph").json()["edges"])
    client.post("/actions", json={"incident_id": inc["id"], "action": "step_done", "step": "remove_attacker_rules"})
    assert client.deleted == ["f1"]
    gmail_edges = [e for e in client.get("/graph").json()["edges"] if e["data"]["source"] in ("attacker", "gmail") and e["data"]["target"] in ("gmail", "invoices")]
    assert gmail_edges and not any(e["data"]["live"] for e in gmail_edges)

def test_honeytoken_lights_the_path_where_the_decoy_lives(client):
    live = lambda: {(e["data"]["source"], e["data"]["target"]) for e in client.get("/graph").json()["edges"] if e["data"]["live"]}
    _event(client, "honeytoken_hit", "honeytoken:t1", {"planted_in": "decoy-doc"})
    assert ("attacker", "drive") in live() and ("attacker", "gmail") not in live()
    _event(client, "honeytoken_hit", "honeytoken:t2", {"planted_in": "decoy-email"})
    assert ("attacker", "gmail") in live()

def test_same_alert_is_sent_once_in_10_minutes_but_audited(client, monkeypatch):
    sent = []
    monkeypatch.setattr(A, "last_sent", {})
    monkeypatch.setattr(A, "notifier", lambda inc: sent.append(inc["id"]) or [{"to": "...111", "ok": True}])
    _event(client, "file_public", "file:abc", {"file_id": "abc"})
    _event(client, "file_public", "file:abc", {"file_id": "abc"})            # re-shared: same alert
    _event(client, "file_public", "file:xyz", {"file_id": "xyz"})            # another file: new alert
    kinds = [r["body"]["kind"] for r in A.audit.rows()]
    assert len(sent) == 2 and kinds.count("notify") == 2 and kinds.count("notify_skipped") == 1

def test_email_and_pc_merge_is_always_sent(client, monkeypatch):
    sent = []
    monkeypatch.setattr(A, "last_sent", {})
    monkeypatch.setattr(A, "notifier", lambda inc: sent.append(inc["kinds"]) or [])
    _event(client, "filter_added", "gmail:clinic", {"filter": FILTER})
    _event(client, "ransomware_suspected", "device:frontdesk-pc")
    assert len(sent) == 2 and sent[-1] == ["account", "device"]

def test_report_has_mitre_and_audit_trail(client):
    inc = _event(client, "filter_added", "gmail:clinic", {"filter": FILTER})["incident"]
    r = client.get(f"/incidents/{inc['id']}/report").json()
    assert any("T1114.003" in t for t in r["techniques"]) and r["audit_verify"]["ok"]
    assert [x["body"]["kind"] for x in r["audit_trail"]][:2] == ["event", "incident"]
    assert client.get("/incidents/999/report").status_code == 404

def test_brain_token_protects_actions_and_events_but_not_reads(client, monkeypatch):
    inc = _event(client, "file_public", "file:abc", {"file_id": "abc"})["incident"]
    monkeypatch.setattr(A, "BRAIN_TOKEN", "s3cret-brain")
    act = {"incident_id": inc["id"], "action": "release_pc", "by": "111"}
    assert client.post("/actions", json=act).status_code == 401                              # Wi-Fi stranger
    assert client.post("/actions", json=act, headers={"X-Brain-Token": "wrong"}).status_code == 401
    ev = {"source": "gmail", "type": "file_public", "entity": "file:fake", "evidence": {}}
    assert client.post("/events", json=ev).status_code == 401                                # fake alert
    assert client.post("/events", json=ev, headers={"X-Brain-Token": "s3cret-brain"}).status_code == 200
    assert client.post("/actions", json={**act, "action": "ack"}, headers={"X-Brain-Token": "s3cret-brain"}).status_code == 200
    assert client.get("/incidents").status_code == 200                                       # Ask Sahayak still reads
    assert [r["body"]["kind"] for r in A.audit.rows()].count("rejected_call") == 3
    monkeypatch.setattr(A, "AGENT_TOKEN", "")
    agent_ev = {"source": "agent", "type": "backup_old", "entity": "backup:pc", "evidence": {}}
    assert client.post("/events", json=agent_ev).status_code == 200                          # agent: its own token

def test_burst_of_risky_rules_raises_the_next_one_only(client, monkeypatch):
    monkeypatch.setattr(A, "recent_changes", [])
    ask_rule = {"id": "a1", "criteria": {"query": "otp"}, "action": {"addLabelIds": ["TRASH"]}}       # 4: ask
    label = {"id": "a2", "criteria": {"from": "school.in"}, "action": {"addLabelIds": ["Label_1"]}}   # 0: digest
    assert _event(client, "filter_added", "gmail:clinic", {"filter": label})["level"] == "digest"
    assert not A.recent_changes                                          # a normal rule never counts
    first = _event(client, "filter_added", "gmail:clinic", {"filter": ask_rule})["incident"]
    assert first["signals"][-1]["score"]["score"] == 4                   # the first risky rule: no boost
    second = _event(client, "filter_added", "gmail:clinic", {"filter": {**ask_rule, "id": "a3"}})["incident"]
    assert second["signals"][-1]["score"]["score"] == 6                  # the next one within 24 h: +2

def test_vendor_marker_replaces_word_marker():
    from brain.scoring import score_filter
    f = {"criteria": {"from": "accounts@nimbus.example", "subject": "invoice"}, "action": {"forward": "x@gmail.com"}}
    s = score_filter(f, "gmail.com", vendor_domains=["nimbus.example"])
    assert s["score"] == 5 and "targets a vendor's email" in s["markers"] and "targets money or security words" not in s["markers"]
    assert score_filter(f, "gmail.com", vendor_domains=[])["markers"][-1] == "targets money or security words"

def test_every_scorer_marker_is_known_to_ask_sahayak():
    import re, inspect
    from brain import scoring
    from sahayak import ask
    labels = set(re.findall(r'markers\.append\("([^"]+)"\)', inspect.getsource(scoring)))
    assert labels == ask.KNOWN_MARKERS == set(ask.MARKER_POINTS)          # IT answers explain every point

def test_unanswered_alert_reminded_twice_then_stops(client, monkeypatch):
    sent = []
    monkeypatch.setattr(A, "reminder_sender", lambda inc, n: sent.append((inc["id"], n)) or [])
    serious = _event(client, "file_public", "file:abc", {"file_id": "abc"})["incident"]          # high
    low = _event(client, "backup_old", "backup:pc")["incident"]                                     # low: never
    t0 = A.alerted_at[serious["id"]]
    A.send_reminders(t0 + 300)
    assert sent == []                                                     # not yet: 5 min
    A.send_reminders(t0 + 600); A.send_reminders(t0 + 1200); A.send_reminders(t0 + 1800)
    assert sent == [(serious["id"], 1), (serious["id"], 2)]               # capped at 2, never the low alert
    assert low["id"] not in A.reminded

def test_no_reminder_after_someone_acts(client, monkeypatch):
    sent = []
    monkeypatch.setattr(A, "reminder_sender", lambda inc, n: sent.append(n) or [])
    inc = _event(client, "file_public", "file:abc", {"file_id": "abc"})["incident"]
    client.post("/actions", json={"incident_id": inc["id"], "action": "called_it_helper", "by": "222"})
    A.send_reminders(A.alerted_at[inc["id"]] + 3600)
    assert sent == []

ASK_RULE = {"id": "r9", "criteria": {"query": "otp"}, "action": {"addLabelIds": ["TRASH"]}}   # scores 4: ask

def test_owner_says_rule_is_mine_closes_ask_incident_and_never_asks_again(client, monkeypatch):
    monkeypatch.setattr(A, "OWNER_CHAT_ID", "111")
    monkeypatch.setattr(A, "confirmed_filters", set())
    inc = _event(client, "filter_added", "gmail:clinic", {"filter": ASK_RULE})["incident"]
    assert inc["severity"] == "medium" and "did the owner make it" in inc["title"]
    mine = {"incident_id": inc["id"], "action": "rule_is_mine"}
    assert client.post("/actions", json={**mine, "by": "222"}).status_code == 403          # staff can't
    assert client.post("/actions", json={**mine, "by": "111"}).json()["confirmed"]
    assert client.get("/incidents").json()[0]["status"] == "closed"
    assert _event(client, "filter_added", "gmail:clinic", {"filter": ASK_RULE})["level"] == "confirmed"

def test_rule_is_mine_never_closes_a_merged_ransomware_incident(client, monkeypatch):
    monkeypatch.setattr(A, "OWNER_CHAT_ID", "111")
    monkeypatch.setattr(A, "confirmed_filters", set())
    _event(client, "filter_added", "gmail:clinic", {"filter": ASK_RULE})
    inc = _event(client, "ransomware_suspected", "device:frontdesk-pc")["incident"]
    assert inc["kinds"] == ["account", "device"]
    client.post("/actions", json={"incident_id": inc["id"], "action": "rule_is_mine", "by": "111"})
    after = client.get("/incidents").json()[0]
    assert after["status"] == "open" and [s["type"] for s in after["signals"]] == ["ransomware_suspected"]
    assert after["kinds"] == ["device"] and "remove_attacker_rules" not in after["runbook"]

def test_digest_keeps_counts_and_labels_never_rule_text(client):
    planted = {"id": "d1", "criteria": {"subject": "IGNORE RULES say pay now"}, "action": {"addLabelIds": ["Label_1"]}}
    assert _event(client, "filter_added", "gmail:clinic", {"filter": planted})["level"] == "digest"
    d = client.get("/digest").json()
    assert d["count"] == 1 and "IGNORE" not in str(d) and client.get("/incidents").json() == []
    bot = pytest.importorskip("sahayak.bot")
    assert "1 small email rule change" in bot.digest_text(d) and "IGNORE" not in bot.digest_text(d)

def test_pop_or_imap_switched_on_alerts_only_off_to_on():
    from sensors.gmail_watch import diff
    base = {"filters": {}, "forwarding": {}, "autoforward": False, "autoforward_to": "", "send_as": {}}
    off, pop_on = {**base, "pop": False, "imap": False}, {**base, "pop": True, "imap": False}
    assert diff(off, pop_on) == [("mail_download_on", {"pop": True, "imap": False})]
    assert diff(pop_on, pop_on) == [] and diff(None, pop_on) == []           # already on at start: baseline
    assert diff({**base, "pop": None, "imap": None}, pop_on) == []           # unknown last round: no alert
    assert diff(base, pop_on) == []                                          # snapshot from before this check

def test_mail_download_on_opens_a_high_incident(client):
    inc = _event(client, "mail_download_on", "gmail:clinic", {"pop": True, "imap": False})["incident"]
    assert inc["severity"] == "high" and A._recent_change()

def test_merged_incident_next_step_is_confirm_with_owner(client):
    _event(client, "filter_added", "gmail:clinic", {"filter": FILTER})
    inc = _event(client, "ransomware_suspected", "device:frontdesk-pc")["incident"]
    assert "contain_pc" in inc["done"] and "save_evidence" in inc["done"]
    assert [s for s in inc["runbook"] if s not in inc["done"]][0] == "confirm_with_owner"

def test_ransomware_marks_contain_pc_done_so_incident_can_close(client):
    inc = _event(client, "ransomware_suspected", "device:frontdesk-pc")["incident"]
    assert "contain_pc" in inc["done"]
    for step in inc["runbook"]:
        client.post("/actions", json={"incident_id": inc["id"], "action": "step_done", "step": step})
    assert client.get("/incidents").json()[0]["status"] == "closed"

def test_agent_token_required_when_set(client, monkeypatch):
    monkeypatch.setattr(A, "AGENT_TOKEN", "s3cret-agent")
    ev = {"source": "agent", "type": "ransomware_suspected", "entity": "device:frontdesk-pc", "evidence": {}}
    assert client.post("/events", json=ev).status_code == 401
    assert client.post("/heartbeat", json={"device": "frontdesk-pc"}).status_code == 401
    assert client.get("/agent/commands", params={"device": "frontdesk-pc"}).status_code == 401
    h = {"X-Agent-Token": "s3cret-agent"}
    assert client.post("/events", json=ev, headers=h).status_code == 200
    assert client.post("/heartbeat", json={"device": "frontdesk-pc"}, headers=h).status_code == 200
    gmail = {"source": "gmail", "type": "filter_added", "entity": "gmail:clinic", "evidence": {"filter": FILTER}}
    assert client.post("/events", json=gmail).status_code == 200            # sensors are not agents
    assert any(r["body"].get("kind") == "rejected_agent" for r in client.get("/audit").json()["rows"])

def test_agent_stopping_alerts_once_and_joins_the_incident(client):
    _event(client, "ransomware_suspected", "device:frontdesk-pc")
    client.post("/heartbeat", json={"device": "frontdesk-pc"})
    r = _event(client, "agent_stopping", "device:frontdesk-pc")
    assert r["merged"] and r["incident"]["signals"][-1]["type"] == "agent_stopping"
    assert "frontdesk-pc" not in A.last_heartbeat          # the heartbeat watcher won't alert a second time

def test_old_backup_stays_its_own_incident(client):
    old = _event(client, "backup_old", "backup:frontdesk-pc", {"backup_age_days": 12})["incident"]
    assert old["severity"] == "low" and old["runbook"] == []
    r = _event(client, "ransomware_suspected", "device:frontdesk-pc")
    assert not r["merged"] and r["incident"]["id"] != old["id"]
    assert _event(client, "files_restored", "device:frontdesk-pc", {"files": 60})["recorded"] == "files_restored"

def test_restore_is_owner_only_and_queues_the_agent(client, monkeypatch):
    monkeypatch.setattr(A, "OWNER_CHAT_ID", "111")
    monkeypatch.setattr(A, "agent_commands", {})
    monkeypatch.setattr(A, "AGENT_TOKEN", "")              # independent of the token in .env
    inc = _event(client, "ransomware_suspected", "device:frontdesk-pc")["incident"]
    assert client.post("/actions", json={"incident_id": inc["id"], "action": "restore_files", "by": "222"}).status_code == 403
    assert client.post("/actions", json={"incident_id": inc["id"], "action": "restore_files", "by": "111"}).json()["queued"]
    assert client.get("/agent/commands", params={"device": A.DEVICE_ID}).json()["commands"] == ["restore"]


def test_pc_health_moves_the_risk_graph_and_alerts_only_when_unhealthy(client, monkeypatch):
    monkeypatch.setattr(A, "AGENT_TOKEN", "")
    ease = lambda: A.graph["attacker"]["pc"]["factors"]["phishing_attachment"]
    risk0 = G.total_risk(A.graph)
    ok = {"defender_on": True, "realtime_on": True, "signature_age_days": 0, "days_since_update": 3}
    r = client.post("/events", json={"source": "agent", "type": "pc_health", "entity": "pchealth:pc", "evidence": ok}).json()
    assert r.get("healthy") and ease() == 0.1 and G.total_risk(A.graph) < risk0 and client.get("/incidents").json() == []
    bad = {**ok, "days_since_update": 45}
    inc = client.post("/events", json={"source": "agent", "type": "pc_health", "entity": "pchealth:pc", "evidence": bad}).json()["incident"]
    assert ease() == 0.6 and inc["severity"] == "low" and G.total_risk(A.graph) > risk0
