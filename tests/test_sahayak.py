"""Aradhya's tests:  python -m pytest tests -q"""
import time, pytest
from sahayak import signing
from sahayak.messages import jargon_ok, TEMPLATES
from sahayak.notify import render, buttons_for

def test_signed_tap_once_only():
    d = signing.make(7, "rm")
    assert len(d.encode()) <= 64
    assert signing.verify(d) == (7, "rm")
    with pytest.raises(signing.BadTap):
        signing.verify(d)                                    # replay

def test_tampered_and_expired_rejected():
    d = signing.make(7, "rm")
    with pytest.raises(signing.BadTap):
        signing.verify(d.replace("|rm|", "|rel|"))          # tampered
    with pytest.raises(signing.BadTap):
        signing.verify(signing.make(8, "rm", ttl=1), now=time.time() + 5)   # expired

def test_english_templates_pass_jargon_check():
    for t in TEMPLATES.values():
        assert jargon_ok(t["en"]), t["en"]
    assert not jargon_ok("Your firewall blocked port 445")

def test_merged_incident_shows_first_step_and_owner_release():
    inc = {"id": 3, "title": "x", "severity": "critical", "kinds": ["account", "device"],
           "signals": [{"type": "ransomware_suspected"}], "done": [],
           "runbook": ["contain_pc", "save_evidence"]}
    text, stype = render(inc)
    assert stype == "merged" and text.startswith("Sahayak · Code")
    labels = [l for l, _ in buttons_for(inc, stype, is_owner=True)]
    assert labels[0].startswith("Done:") and "Owner: release the PC" in labels
    assert "Owner: release the PC" not in [l for l, _ in buttons_for(inc, stype, is_owner=False)]
