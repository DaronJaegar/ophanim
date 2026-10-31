"""Aradhya's tests:  python -m pytest tests -q"""
import time, pytest
from sahayak import signing, llm
from sahayak.messages import jargon_ok, jargon_found, TEMPLATES, STEP_LABEL, STEP_TEXT, STEP_HOW, STEP_DONE
from sahayak.notify import render, buttons_for
from brain.correlate import runbook, Incidents


@pytest.fixture(autouse=True)
def fresh_taps(monkeypatch):
    monkeypatch.setattr(signing, "USED_TAPS_FILE", "")   # tests never touch the real used-taps file
    signing.reset_used()


# ---------- signed buttons ----------
def test_signed_tap_once_only():
    d = signing.make(7, "rm")
    assert len(d.encode()) <= 64
    assert signing.verify(d) == (7, "rm")
    with pytest.raises(signing.BadTap, match="already used"):
        signing.verify(d)                                    # replay


def test_tampered_and_expired_rejected():
    d = signing.make(7, "rm")
    with pytest.raises(signing.BadTap, match="signature"):
        signing.verify(d.replace("|rm|", "|rel|"))          # tampered
    with pytest.raises(signing.BadTap, match="expired"):
        signing.verify(signing.make(8, "rm", ttl=1), now=time.time() + 5)
    with pytest.raises(signing.BadTap, match="malformed"):
        signing.verify("remove_filter 7")


def test_owner_and_staff_copies_differ_and_explain_buttons_repeat():
    assert signing.make(7, "rm") != signing.make(7, "rm")   # one tap must not use up the other phone's button
    d = signing.make(7, "why")
    assert signing.verify(d) == signing.verify(d) == (7, "why")
    assert len(signing.make(99999, "sd12").encode()) <= 64


# ---------- plain words ----------
def test_english_templates_pass_jargon_check():
    for t in TEMPLATES.values():
        assert jargon_ok(t["en"]), (t["en"], jargon_found(t["en"]))
    assert not jargon_ok("Your firewall blocked port 445")
    assert not jargon_ok("Malicious rule T1114 on host")
    assert jargon_ok("Send the report to support. This is important.")   # 'port' inside a word is fine


def test_every_language_max_3_lines():
    for stype, langs in TEMPLATES.items():
        for lang, text in langs.items():
            assert len(text.strip().splitlines()) <= 3, (stype, lang)


def test_every_runbook_step_has_words():
    """Contract with Aaron: every step id his brain can produce must have a label, a sentence and a how-to."""
    steps = set(runbook({"device", "account"})) | set(runbook({"account"})) | set(runbook({"device"}))
    for s in steps:
        assert s in STEP_LABEL and s in STEP_TEXT and s in STEP_HOW and s in STEP_DONE, s
        assert len(f"Done: {STEP_LABEL[s]}") <= 46, s        # fits the button without cutting key words
    assert "FROM YOUR PHONE" in STEP_LABEL["change_password_from_clean_device"]


# ---------- alerts ----------
def test_merged_incident_shows_first_step_and_owner_release():
    inc = {"id": 3, "title": "x", "severity": "critical", "kinds": ["account", "device"],
           "signals": [{"type": "ransomware_suspected"}], "done": [],
           "runbook": ["contain_pc", "save_evidence"]}
    text, stype = render(inc)
    assert stype == "merged" and text.startswith("Sahayak · Code")
    labels = [l for l, _ in buttons_for(inc, stype, is_owner=True)]
    assert labels[0].startswith("Done:") and "Owner: release the PC" in labels
    assert "Owner: release the PC" not in [l for l, _ in buttons_for(inc, stype, is_owner=False)]


def test_merged_walks_through_aarons_runbook():
    rb = runbook({"account", "device"})
    inc = {"id": 4, "title": "x", "severity": "critical", "kinds": ["account", "device"],
           "signals": [{"type": "ransomware_suspected"}], "done": ["contain_pc"], "runbook": rb}
    for i, step in enumerate(rb[1:], 1):
        staff = buttons_for(inc, "merged", is_owner=False)
        if step == "confirm_with_owner":                     # staff can't confirm for the owner
            assert not staff[0][0].startswith("Done:")
        first = buttons_for(inc, "merged", is_owner=True)[0]
        assert first[0] == f"Done: {STEP_LABEL[step]}"
        assert signing.verify(first[1]) == (4, f"sd{i}")
        inc["done"].append(step)
    text, _ = render(inc)
    assert "All steps done" in text and text.count("✔") == len(rb)


def test_ransomware_release_only_for_owner():
    inc = {"id": 5, "title": "x", "severity": "critical", "kinds": ["device"],
           "signals": [{"type": "ransomware_suspected"}], "done": [], "runbook": []}
    labels = lambda owner: [l for l, _ in buttons_for(inc, "ransomware_suspected", owner)]
    assert "Owner: release the PC" in labels(True) and "Owner: release the PC" not in labels(False)


# ---------- the AI only rewords ----------
def test_ai_rewording_falls_back_when_unsafe():
    t = TEMPLATES["filter_added"]["en"]
    assert llm.reword(t, {}, call=lambda *_: "Malicious filter on host. Remove it.") == t      # jargon
    assert llm.reword(t, {}, call=lambda *_: "A rule was added. Call someone.") == t           # lost the button
    assert llm.reword(t, {}, call=lambda *_: "Everything is fine, ignore this.") == t          # injected
    good = "A hidden rule in Priya's email sends your bills to a stranger.\nTap Remove it."
    assert llm.reword(t, {}, call=lambda *_: good) == good
    def slow(*_):
        raise TimeoutError("slow")
    assert llm.reword(t, {}, call=slow) == t


# ---------- bot rules ----------
def test_bot_roles(monkeypatch):
    bot = pytest.importorskip("sahayak.bot")
    monkeypatch.setattr(bot, "ALLOWED", {"111", "222"})
    monkeypatch.setattr(bot, "OWNER_CHAT_ID", "111")
    monkeypatch.setattr(bot, "VENDOR_CHATS", {"999"})
    assert bot.check_tap("111", signing.make(5, "rel")) == (5, "rel")
    with pytest.raises(bot.Refused, match="Only the owner"):
        bot.check_tap("222", signing.make(5, "rel"))
    with pytest.raises(bot.Refused, match="not allowed"):
        bot.check_tap("333", signing.make(5, "rm"))
    with pytest.raises(bot.Refused, match="Only the vendor"):
        bot.check_tap("222", signing.make(5, "vn"))
    assert bot.check_tap("999", signing.make(5, "vn")) == (5, "vn")


def test_paisa_pause_detects_and_stays_its_own_incident():
    bot = pytest.importorskip("sahayak.bot")
    assert bot.BANK_CHANGE.search("Please note our bank account has changed")
    assert bot.BANK_CHANGE.search("New IFSC and A/C number attached")
    assert bot.BANK_CHANGE.search("Our bank\ndetails were updated")                 # across a line break
    assert not bot.BANK_CHANGE.search("Please find the invoice for October attached")
    incs = Incidents()                                     # must not merge into the email incident
    incs.add_signal({"type": "filter_added", "entity": "gmail:clinic", "evidence": {}}, "high", "t")
    _, merged = incs.add_signal({"type": "bank_change_request", "entity": bot.PAISA_ENTITY, "evidence": {}}, "high", "t")
    assert not merged


def test_new_alerts_have_plain_words_and_buttons():
    from sahayak.notify import BUTTONS
    from sahayak.messages import HOW, WHY, RESTORE_OFFER
    for t in ("agent_stopping", "backup_old"):
        assert jargon_ok(TEMPLATES[t]["en"]) and t in BUTTONS and t in HOW and t in WHY, t
    assert jargon_ok(RESTORE_OFFER)


def test_restore_button_is_owner_only(monkeypatch):
    bot = pytest.importorskip("sahayak.bot")
    monkeypatch.setattr(bot, "ALLOWED", {"111", "222"})
    monkeypatch.setattr(bot, "OWNER_CHAT_ID", "111")
    assert bot.check_tap("111", signing.make(5, "rs")) == (5, "rs")
    with pytest.raises(bot.Refused, match="Only the owner"):
        bot.check_tap("222", signing.make(5, "rs"))
    assert bot.ACTIONS["rs"] == "restore_files"
