"""Ask Sahayak: 20 real-life scenarios for a clinic (Aradhya, Module D).
Each scenario checks: the right guide (or behaviour), the key advice is in the reply, and nothing dangerous.
Runs without the AI (worst case: staff get our own guide text).   python -m pytest tests -q"""
import time
import pytest
from sahayak import ask

PC_ATTACK = {"id": 2, "status": "open", "title": "Your front-desk computer started locking files",
             "severity": "critical", "kinds": ["device"], "policy": "auto",
             "signals": [{"type": "ransomware_suspected",
                          "evidence": {"signals": {"decoy": True, "entropy": True, "rename": True},
                                       "contained": True, "seconds_to_contain": 3}}],
             "runbook": ["contain_pc", "change_password_from_clean_device", "sign_out_other_devices",
                         "check_payments", "report"], "done": ["contain_pc"]}
BOTH = {"id": 3, "status": "open", "title": "Priya's email and her computer are both under attack",
        "severity": "critical", "kinds": ["account", "device"], "policy": "auto",
        "signals": [{"type": "filter_added", "evidence": {}, "score": {"score": 7, "markers": [
            "sends mail to another account", "hides mail", "targets money or security words"]}}] + PC_ATTACK["signals"],
        "runbook": ["contain_pc", "save_evidence", "confirm_with_owner", "remove_attacker_rules",
                    "change_password_from_clean_device"], "done": ["contain_pc", "save_evidence"]}

# (scenario, message, open alerts, expected guide id or behaviour, phrases the reply must contain)
SCENARIOS = [
    # --- account hacked ---
    ("Email hacked", "my email account got hacked what do i do", [], "hacked", ["from your phone", "sign out"]),
    ("Password changed by someone", "someone changed our gmail password i cant login", [], "login", ["Forgot password"]),
    ("Someone reading our mail", "i think someone is reading our clinic emails", [], "hacked", ["password"]),
    ("Invoices vanish from inbox", "invoices are not coming to inbox anymore", [], "rule", ["rule"]),
    # --- ransomware ---
    ("Files renamed .locked", "all files on reception pc have .locked at the end", [], "locked", ["Do not switch"]),
    ("Ransom note on screen", "screen says pay bitcoin to get files back", [], "locked", ["Do not switch"]),
    ("Wants to switch PC off", "files are getting locked should i turn off the computer", [], "locked", ["Do not switch"]),
    ("Why ransomware? (live)", "how do you know it's ransomware", [PC_ATTACK], "ALERT", ["3 of 3 signs", "in 3 seconds"]),
    # --- bank and money ---
    ("Bank details stolen", "someone stole our bank details, they know our account number and ifsc", [], "bankstolen",
     ["Call your bank"]),
    ("Card used on fake site", "i entered our debit card details on a fake website", [], "bankstolen", ["block"]),
    ("OTP already given", "i gave the otp to a caller from the bank", [], "otpshared", ["Call your bank"]),
    ("Unknown debit", "money was debited from clinic account and we didn't do it", [], "money", ["1930"]),
    ("Vendor changes account", "vendor whatsapp says new account number pay there", [], "bill", ["Don't pay yet"]),
    # --- files, decoys, protection ---
    ("Patient file public", "patient records file is shared publicly on drive", [], "public", ["Make it private"]),
    ("Decoy opened", "someone opened the netbanking login file", [], "decoy", ["intruder"]),
    ("Protection stopped", "the computer protection stopped working", [], "stopped", ["IT helper"]),
    # --- scams aimed at staff ---
    ("Fake tech support", "a caller says he is from microsoft and needs anydesk", [], "remote", ["Don't install"]),
    ("Boss gift-card scam", "doctor messaged from new number asking for gift cards", [], "giftcard", ["saved number"]),
    # --- the live alert and guard rails ---
    ("What's happening (live)", "what is happening to my system", [BOTH], "ALERT", ["joined into one incident", "Next step:"]),
    ("Hacking request", "how do i hack into my ex colleague's gmail", [], "REFUSE", []),
]


@pytest.mark.parametrize("name,message,alerts,expect,phrases", SCENARIOS, ids=[s[0] for s in SCENARIOS])
def test_scenario(monkeypatch, name, message, alerts, expect, phrases):
    monkeypatch.setattr(ask, "LLM_API_KEY", "")                        # worst case: no AI at all
    text, source, _ = ask.answer(message, alerts, chat=f"scn-{time.time()}")
    if expect == "ALERT":
        assert source == "This alert's details", text
    elif expect == "REFUSE":
        assert text == ask.REFUSE
    else:
        assert source == ask.BY_ID[expect]["title"], f"{name}: got {source!r}"
    for p in phrases:
        assert p.lower() in text.lower(), f"{name}: missing {p!r} in:\n{text}"
    assert not ask.dangerous(text), f"{name}: unsafe advice:\n{text}"


def test_twenty_scenarios():
    assert len(SCENARIOS) == 20


def test_no_guide_is_flagged_unsafe():
    """Our own guide text must never trip the safety filter, or good AI answers get thrown away."""
    for g in ask.GUIDES:
        for line in list(g["lines"]) + list(g["steps"]):
            assert not ask.dangerous(line), f"{g['id']}: {line}"


def test_alert_step_does_not_repeat_forever(monkeypatch):
    """Asking "what now?" again must not just repeat the same step: it says why it is waiting."""
    import copy
    from sahayak.messages import jargon_ok
    monkeypatch.setattr(ask, "LLM_API_KEY", "")
    chat, inc = f"rep-{time.time()}", copy.deepcopy(PC_ATTACK)
    first, src, _ = ask.answer("what should i do", [inc], chat=chat)
    assert "YOUR PHONE" in first and "(2 of 5)" in src
    again, _, _ = ask.answer("what now", [inc], chat=chat)
    assert again != first and "still on step 2 of 5" in again and "taps \"Done:" in again
    why, src, _ = ask.answer("why", [inc], chat=chat)
    assert src == "Why this step" and "phone is safe" in why
    said_done, _, _ = ask.answer("done", [inc], chat=chat)
    assert 'tap "Done:' in said_done and "sign out all other devices" in said_done
    inc["done"].append("change_password_from_clean_device")          # someone tapped the Done button
    moved, src, _ = ask.answer("what now", [inc], chat=chat)
    assert "(3 of 5)" in src and "sign out" in moved.lower()
    for text in (again, why, said_done):
        assert jargon_ok(text) and not ask.dangerous(text)


def test_done_without_an_alert_is_just_thanks(monkeypatch):
    monkeypatch.setattr(ask, "LLM_API_KEY", "")
    assert ask.answer("done", [], chat="d1")[0] == ask.THANKS
