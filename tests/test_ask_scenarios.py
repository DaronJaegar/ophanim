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


# ---------- "Is this link safe?" (sahayak/urlcheck.py): offline rules, never the AI ----------
LINKS = [  # (message staff forward, expected warning words or None = no sign found)
    ("Dear customer KYC expires today https://sbi-kyc-update.com/verify", "pretends to be SBI"),
    ("hdfc alert http://hdfcbnak.com/login", "pretends to be HDFC Bank"),
    ("track your parcel https://bit.ly/3abc", "short link"),
    ("install this to get the refund https://apps.example.in/refund.apk", "downloads a program"),
    ("login here https://paytm.com@evil.example/login", "@ sign"),
    ("lunch order https://zomato.com/order", None),
    ("report is here https://drive.google.com/file/d/1", None),
]


def test_link_check_warns_on_scam_links_and_never_says_safe():
    from sahayak import urlcheck
    for msg, want in LINKS:
        reply = urlcheck.check_text(msg)
        assert "safe." not in reply.replace("can't be sure it's safe", "")        # never "this is safe"
        if want:
            assert reply.startswith(urlcheck.CAREFUL) and want in reply, msg
        else:
            assert reply == urlcheck.NORMAL, msg
        assert not ask.dangerous(reply)


def test_link_messages_never_reach_ask_or_the_ai(monkeypatch):
    bot = pytest.importorskip("sahayak.bot")
    monkeypatch.setattr(bot, "ALLOWED", {"222"})
    monkeypatch.setattr(bot, "IT_CHAT_ID", "555")
    assert bot.route("222", "is this real? https://sbi-kyc-update.com") == "link"
    assert bot.route("555", "check www.amazon-offers.xyz/win") == "link"
    assert bot.route("222", "our bank account changed, new details https://x.in/b") == "paisa"   # Paisa Pause first
    assert bot.route("222", "is this link safe?") == "ask"                                     # no link: a question
    assert bot.route("999", "https://bit.ly/x") == "ignore"                                    # unknown phones
    assert ask.search("is this link safe")[0][1]["id"] == "urlcheck"


@pytest.mark.parametrize("message,expect", [
    ("call it help", ["IT helper: 9000000001"]), ("call IT", ["IT helper: 9000000001"]),
    ("it helper number", ["IT helper: 9000000001"]), ("give me the it guy's phone", ["IT helper: 9000000001"]),
    ("owner number pls", ["Owner: 9000000002"]), ("call the doctor", ["Owner: 9000000002"]),
    ("staff number", ["Front desk: 9000000003"]), ("reception phone number", ["Front desk: 9000000003"]),
    ("who do i call", ["IT helper: 9000000001", "Owner: 9000000002", "Front desk: 9000000003", "1930"]),
])
def test_phone_numbers_on_request(monkeypatch, message, expect):
    from common import config
    monkeypatch.setattr(ask, "LLM_API_KEY", "")
    for k, v in {"IT_PHONE": "9000000001", "OWNER_PHONE": "9000000002", "CLINIC_PHONE": "9000000003",
                 "OWNER_NAME": "the owner", "IT_NAME": "", "STAFF_NAME": "", "VENDOR_NAME": ""}.items():
        monkeypatch.setattr(config, k, v)
    text, src, _ = ask.answer(message, [], chat=f"num-{time.time()}")
    assert src == ask.CONTACT_SOURCE, (message, text)
    for e in expect:
        assert e in text, (message, text)


@pytest.mark.parametrize("message", ["someone called me from tech support asking for my password",
                                     "a caller wants the otp", "should i call the bank", "can i call it a false alarm",
                                     "is it safe to open this file"])
def test_contact_questions_dont_steal_other_questions(monkeypatch, message):
    monkeypatch.setattr(ask, "LLM_API_KEY", "")
    assert ask.answer(message, [], chat=f"nc-{time.time()}")[1] != ask.CONTACT_SOURCE, message


def test_missing_number_is_said(monkeypatch):
    from common import config
    monkeypatch.setattr(config, "IT_PHONE", "")
    assert "no number saved" in ask.answer("it helper number", [], chat="nn")[0]


def test_names_and_asking_by_first_name(monkeypatch):
    from common import config
    monkeypatch.setattr(ask, "LLM_API_KEY", "")
    for k, v in {"IT_PHONE": "9000000001", "IT_NAME": "Ravi Kumar", "OWNER_PHONE": "9000000002",
                 "OWNER_NAME": "Meera Rao", "CLINIC_PHONE": "9000000003", "STAFF_NAME": "Sita Devi",
                 "VENDOR_NAME": "Anil Supplies", "VENDOR_PHONE": ""}.items():
        monkeypatch.setattr(config, k, v)
    assert "IT helper (Ravi Kumar): 9000000001" in ask.answer("call it help", [], chat="n1")[0]
    assert "IT helper (Ravi Kumar): 9000000001" in ask.answer("call ravi", [], chat="n2")[0]
    assert "Owner (Meera Rao): 9000000002" in ask.answer("meera's number", [], chat="n3")[0]
    assert "Front desk (Sita Devi): 9000000003" in ask.answer("staff number", [], chat="n4")[0]
    assert "Vendor (Anil Supplies): no number saved" in ask.answer("vendor number", [], chat="n5")[0]
    everyone = ask.answer("who do i call", [], chat="n6")[0]
    assert "Ravi" in everyone and "Meera" in everyone and "Sita" in everyone and "Vendor" not in everyone
