"""Aaron's tests:  python -m pytest tests -q"""
from datetime import datetime, timedelta, timezone
from brain import graph as G
from brain.scoring import score_filter
from brain.correlate import Incidents

def test_demo_graph_numbers():
    g = G.build_demo_graph()
    assert G.total_risk(g) == 12.45
    assert sum(p["open"] for p in G.paths(g)) == 4
    f = G.one_fix(g)
    assert f["fix"] == "enable_2sv" and f["paths_closed"] == 2 and f["risk_drop"] == 6.04
    assert G.total_risk(g) == 12.45            # one_fix must not change the real graph

def test_live_then_clear_restores():
    g = G.build_demo_graph()
    G.mark_live(g, "attacker", "gmail"); G.clear_live(g, "attacker", "gmail")
    assert G.total_risk(g) == 12.45

def test_invoice_filter_scores_7():
    f = {"criteria": {"query": "invoice OR payment"}, "action": {"forward": "x@evil.com"}}
    assert score_filter(f, "gmail.com", recent_change=True)["score"] == 7

def test_email_and_pc_merge_but_unrelated_does_not():
    inc = Incidents(); now = datetime.now(timezone.utc)
    a, _ = inc.add_signal({"type": "filter_added", "entity": "gmail:clinic", "evidence": {}}, "high", "t", now=now)
    b, merged = inc.add_signal({"type": "ransomware_suspected", "entity": "device:frontdesk-pc", "evidence": {}},
                               "critical", "t", "auto", now=now + timedelta(minutes=5))
    assert merged and a is b and b["runbook"][0] == "contain_pc" and "change_password_from_clean_device" in b["runbook"]
    _, merged2 = inc.add_signal({"type": "ransomware_suspected", "entity": "device:other-pc", "evidence": {}},
                                "critical", "t", now=now)
    assert not merged2
