"""Plain-language templates and the jargon check (Aradhya, Module D).
Rules: at most 3 short lines, one main button, no jargon. Hindi and Kannada are DRAFTS:
a native speaker must check them before the event."""

TEMPLATES = {
    "filter_added": {
        "en": "Someone set up a hidden rule that sends your invoices to a stranger.\nThis is how invoice fraud starts.\nRemove it?",
        "hi": "किसी ने एक छुपा नियम बनाया है जो आपके बिल (इनवॉइस) किसी अनजान व्यक्ति को भेज रहा है।\nक्या इसे हटा दें?",
        "kn": "ಯಾರೋ ಒಂದು ಗುಪ್ತ ನಿಯಮ ಹೊಂದಿಸಿದ್ದಾರೆ, ಅದು ನಿಮ್ಮ ಇನ್‌ವಾಯ್ಸ್‌ಗಳನ್ನು ಅಪರಿಚಿತರಿಗೆ ಕಳುಹಿಸುತ್ತಿದೆ.\nಅದನ್ನು ತೆಗೆದುಹಾಕಬೇಕೇ?",
    },
    "forwarding_added": {
        "en": "Someone is trying to send copies of your email to a stranger.\nIt hasn't started yet. Tap below to see how to stop it.",
    },
    "autoforward_on": {"en": "All your new email is being copied to a stranger.\nTap below to see how to turn it off."},
    "sendas_added": {"en": "Someone added a new address that can send email as the clinic.\nTap below to see how to remove it."},
    "file_public": {"en": "A private folder can now be opened by anyone on the internet.\nMake it private?"},
    "honeytoken_hit": {"en": "A stranger opened the fake bank login we hid in your files.\nSomeone is reading your documents. Let's lock them out."},
    "ransomware_suspected": {
        "en": "URGENT: Your front-desk computer started locking files.\nWe cut it off from the internet so your other computers stay safe.\nPlease don't switch it off. Your IT helper has been told.",
        "hi": "ज़रूरी: आपके फ्रंट-डेस्क कंप्यूटर की फ़ाइलें लॉक होने लगीं।\nबाकी कंप्यूटरों को बचाने के लिए हमने इसे इंटरनेट से अलग कर दिया है।\nकृपया इसे बंद न करें — आपके आईटी सहायक को बता दिया गया है।",
        "kn": "ತುರ್ತು: ನಿಮ್ಮ ಮುಂಭಾಗದ ಕಂಪ್ಯೂಟರ್‌ನ ಫೈಲ್‌ಗಳು ಲಾಕ್ ಆಗುತ್ತಿವೆ.\nಇತರ ಕಂಪ್ಯೂಟರ್‌ಗಳನ್ನು ರಕ್ಷಿಸಲು ನಾವು ಅದನ್ನು ಇಂಟರ್ನೆಟ್‌ನಿಂದ ಬೇರ್ಪಡಿಸಿದ್ದೇವೆ.\nದಯವಿಟ್ಟು ಅದನ್ನು ಆಫ್ ಮಾಡಬೇಡಿ — ನಿಮ್ಮ ಐಟಿ ಸಹಾಯಕರಿಗೆ ತಿಳಿಸಲಾಗಿದೆ.",
    },
    "heartbeat_missing": {"en": "The protection on the front-desk computer stopped responding.\nSomeone may have switched it off on purpose. Your IT helper has been told."},
    "bank_change_request": {"en": "This message says a vendor's bank details changed.\nDon't pay yet. We'll check with the vendor on the number you already have."},
    "merged": {"en": "Priya's email and her computer are both under attack.\nFollow the steps below, one at a time."},
}

STEP_TEXT = {
    "contain_pc": "The front-desk PC is cut off (done automatically)",
    "save_evidence": "Save the evidence (done automatically)",
    "confirm_with_owner": "Owner: did you create any email rule today?",
    "remove_attacker_rules": "Remove the attacker's email rules",
    "change_password_from_clean_device": "Change Priya's email password FROM YOUR PHONE, not the PC",
    "change_password": "Change Priya's email password",
    "sign_out_other_devices": "Sign out all other devices (Google Account > Security)",
    "check_payments": "Check payments from the last 7 days. Fraud? Call your bank and 1930",
    "report": "Send the report to your IT helper",
}

JARGON = ["ip address", " ip ", "port", "mac address", "dns", "malware", "payload", "oauth", " api",
          "hash", "entropy", "exploit", "mitre", "endpoint", "firewall", "token", "smtp", "nftables"]

def jargon_ok(text):
    t = f" {text.lower()} "
    lines = [l for l in text.strip().splitlines() if l.strip()]
    return len(lines) <= 3 and not any(j in t for j in JARGON)

def template_for(signal_type, lang="en"):
    t = TEMPLATES.get(signal_type, {"en": "Something unusual happened. Your IT helper has been told."})
    return t.get(lang) or t["en"]
