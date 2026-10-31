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
