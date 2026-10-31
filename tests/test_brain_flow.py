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

def test_ransomware_marks_contain_pc_done_so_incident_can_close(client):
    inc = _event(client, "ransomware_suspected", "device:frontdesk-pc")["incident"]
    assert "contain_pc" in inc["done"]
    for step in inc["runbook"]:
        client.post("/actions", json={"incident_id": inc["id"], "action": "step_done", "step": step})
    assert client.get("/incidents").json()[0]["status"] == "closed"
