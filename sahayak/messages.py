"""Plain-language templates and the jargon check (Aradhya, Module D).
Rules for every message: say what happened in her world, why it matters, one clear action,
reassure when we already acted. At most 3 short lines, no jargon, never ask for passwords,
OTPs or payments. Hindi (hi) and Kannada (kn) are DRAFTS: a native speaker must check them
before the event. A type without hi/kn falls back to English."""
import re

TEMPLATES = {
    "filter_added": {
        "en": "Someone set up a hidden rule that sends your invoices to a stranger.\nThis is how invoice fraud starts.\nTap Remove it.",
        "hi": "किसी ने एक छुपा नियम बनाया है जो आपके बिल (इनवॉइस) किसी अनजान व्यक्ति को भेज रहा है।\nबिल-धोखाधड़ी ऐसे ही शुरू होती है।\n'Remove it' दबाएँ।",
        "kn": "ಯಾರೋ ಒಂದು ಗುಪ್ತ ನಿಯಮ ಹೊಂದಿಸಿದ್ದಾರೆ, ಅದು ನಿಮ್ಮ ಇನ್‌ವಾಯ್ಸ್‌ಗಳನ್ನು ಅಪರಿಚಿತರಿಗೆ ಕಳುಹಿಸುತ್ತಿದೆ.\nಬಿಲ್ ವಂಚನೆ ಹೀಗೆಯೇ ಶುರುವಾಗುತ್ತದೆ.\n'Remove it' ಒತ್ತಿ.",
    },
    "filter_ask": {      # a rule that scored 3-4: could be the owner's own, so we ask instead of alarming
        "en": "A new email rule was made in the clinic email today.\nIt could be yours, or a stranger's.\nOwner: tap Yes, it's mine. Otherwise tap No, remove it.",
    },
    "forwarding_added": {
        "en": "Someone is trying to send copies of your email to a stranger.\nIt hasn't started yet, so you can stop it now.\nTap Show me how.",
    },
    "autoforward_on": {
        "en": "All your new email is being copied to a stranger.\nThey can read your bills and patient letters.\nTap Show me how to turn it off.",
    },
    "mail_download_on": {
        "en": "Someone switched on a setting that lets another app download all the clinic email.\nIf nobody at the clinic did this, a stranger may be copying your mail.\nTap Show me how to change the setting back.",
    },
    "sendas_added": {
        "en": "Someone added a new address that can send email as the clinic.\nIt can be used to send fake bills to your patients and vendors.\nTap Show me how to remove it.",
    },
    "file_public": {
        "en": "A private folder can now be opened by anyone on the internet.\nIt may hold patient details.\nTap Make it private.",
    },
    "honeytoken_hit": {
        "en": "A stranger opened the fake bank login we hid in your files.\nSomeone is reading your documents right now.\nTap Start the fix.",
    },
    "ransomware_suspected": {
        "en": "URGENT: Your front-desk computer started locking files.\nWe cut it off from the internet so your other computers stay safe.\nPlease don't switch it off. Tap Okay.",
        "hi": "ज़रूरी: आपके फ्रंट-डेस्क कंप्यूटर की फ़ाइलें लॉक होने लगीं।\nबाकी कंप्यूटरों को बचाने के लिए हमने इसे इंटरनेट से अलग कर दिया है।\nकृपया इसे बंद न करें। 'Okay' दबाएँ।",
        "kn": "ತುರ್ತು: ನಿಮ್ಮ ಮುಂಭಾಗದ ಕಂಪ್ಯೂಟರ್‌ನ ಫೈಲ್‌ಗಳು ಲಾಕ್ ಆಗುತ್ತಿವೆ.\nಇತರ ಕಂಪ್ಯೂಟರ್‌ಗಳನ್ನು ರಕ್ಷಿಸಲು ನಾವು ಅದನ್ನು ಇಂಟರ್ನೆಟ್‌ನಿಂದ ಬೇರ್ಪಡಿಸಿದ್ದೇವೆ.\nದಯವಿಟ್ಟು ಅದನ್ನು ಆಫ್ ಮಾಡಬೇಡಿ. 'Okay' ಒತ್ತಿ.",
    },
    "heartbeat_missing": {
        "en": "The protection on the front-desk computer stopped responding.\nSomeone may have switched it off on purpose.\nTap Call my IT helper.",
    },
    "agent_stopping": {
        "en": "The protection on the front-desk computer was switched off.\nIf nobody at the clinic did this, someone may be hiding an attack.\nTap Call my IT helper.",
    },
    "backup_old": {
        "en": "The newest copy of your clinic files is more than a week old.\nIf files get locked, you would lose a week of work.\nTap Show me how to make a fresh copy today.",
    },
    "pc_health": {
        "en": "The front-desk computer is missing safety updates, or its virus protection is off.\nThat makes it easier for someone to lock your files.\nTap Show me how.",
    },
    "bank_change_request": {
        "en": "Don't pay yet. This message says a vendor's bank details changed.\nThat is the most common way clinics lose money.\nTap Check with the vendor: we'll ask on the number you saved.",
        "hi": "अभी भुगतान न करें। इस संदेश में लिखा है कि विक्रेता का बैंक खाता बदल गया है।\nक्लिनिक ज़्यादातर ऐसे ही पैसे खोते हैं।\n'Check with the vendor' दबाएँ: हम उनके सेव किए नंबर पर पूछेंगे।",
        "kn": "ಈಗ ಹಣ ಪಾವತಿಸಬೇಡಿ. ಮಾರಾಟಗಾರರ ಬ್ಯಾಂಕ್ ವಿವರ ಬದಲಾಗಿದೆ ಎಂದು ಈ ಸಂದೇಶ ಹೇಳುತ್ತದೆ.\nಕ್ಲಿನಿಕ್‌ಗಳು ಹೆಚ್ಚಾಗಿ ಹೀಗೆಯೇ ಹಣ ಕಳೆದುಕೊಳ್ಳುತ್ತವೆ.\n'Check with the vendor' ಒತ್ತಿ: ನೀವು ಉಳಿಸಿದ ನಂಬರ್‌ನಲ್ಲಿ ನಾವು ಕೇಳುತ್ತೇವೆ.",
    },
    "merged": {
        "en": "Priya's email and her computer are both under attack.\nWe already cut the computer off. Follow the steps below, one at a time.\nTap Done after each step.",
        "hi": "प्रिया का ईमेल और कंप्यूटर, दोनों पर हमला हो रहा है।\nकंप्यूटर हमने अलग कर दिया है। अब नीचे के कदम एक-एक करके करें।\nहर कदम के बाद 'Done' दबाएँ।",
        "kn": "ಪ್ರಿಯಾ ಅವರ ಇಮೇಲ್ ಮತ್ತು ಕಂಪ್ಯೂಟರ್ ಎರಡರ ಮೇಲೂ ದಾಳಿ ನಡೆಯುತ್ತಿದೆ.\nಕಂಪ್ಯೂಟರ್ ಅನ್ನು ನಾವು ಈಗಾಗಲೇ ಬೇರ್ಪಡಿಸಿದ್ದೇವೆ. ಕೆಳಗಿನ ಹಂತಗಳನ್ನು ಒಂದೊಂದಾಗಿ ಮಾಡಿ.\nಪ್ರತಿ ಹಂತದ ನಂತರ 'Done' ಒತ್ತಿ.",
    },
    "unknown": {
        "en": "Something unusual happened in your clinic's accounts.\nYour IT helper can check it.\nTap Call my IT helper.",
    },
    "reminder": {        # sent again when nobody tapped anything on a serious alert for 10 minutes (max 2 times)
        "en": "Reminder: this safety alert is still waiting.\nNobody has tapped a button on it yet.\nTap one below, or call your IT helper.",
    },
}
# Sent to the IT helper with the second reminder.
IT_REMINDER = "Nobody at the clinic has acted on Sahayak alert {iid} for 20 minutes. Please call them."

# Runbook steps. KEYS MUST MATCH brain/correlate.py runbook().
# STEP_LABEL goes on the "Done: ..." button: max 40 characters, so the key words are never cut off.
STEP_LABEL = {
    "contain_pc": "PC is cut off (automatic)",
    "save_evidence": "evidence is saved",
    "confirm_with_owner": "owner made no new email rule today",
    "remove_attacker_rules": "remove the attacker's email rules",
    "change_password_from_clean_device": "change password FROM YOUR PHONE",
    "change_password": "change Priya's email password",
    "sign_out_other_devices": "sign out all other devices",
    "check_payments": "check last 7 days of payments",
    "report": "send the report to your IT helper",
}

# Full sentence for each step (numbered list for "Start the fix", ticks in the merged message).
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

# Tick shown once a step is done.
STEP_DONE = {
    "contain_pc": "Front-desk PC cut off",
    "save_evidence": "Evidence saved",
    "confirm_with_owner": "Owner made no new email rule today",
    "remove_attacker_rules": "Attacker's email rules removed",
    "change_password_from_clean_device": "Password changed from a phone, not the PC",
    "change_password": "Password changed",
    "sign_out_other_devices": "Other devices signed out",
    "check_payments": "Payments checked",
    "report": "IT helper told",
}

# Steps only the owner may mark done.
OWNER_STEPS = {"confirm_with_owner"}

# "Show me how" for the current runbook step.
STEP_HOW = {
    "contain_pc": "Leave the front-desk PC switched on. Don't unplug or restart it.",
    "save_evidence": "Nothing to do: we already saved a copy of the attacker's changes.",
    "confirm_with_owner": "Owner: if you did not make an email rule today, tap Done. If you did, call your IT helper.",
    "remove_attacker_rules": "Tap Done and we delete the attacker's email rules for you.",
    "change_password_from_clean_device": "On YOUR PHONE, not the front-desk PC: Google Account > Security > Password. Choose a new one.",
    "change_password": "Google Account > Security > Password. Choose a new one you haven't used before.",
    "sign_out_other_devices": "Google Account > Security > Your devices > sign out every device you don't recognise.",
    "check_payments": "Look at payments from the last 7 days. If money went somewhere strange, call your bank and 1930.",
    "report": "Tap Done and we'll send the full report to your IT helper.",
}

# "Show me how" for single (non-merged) alerts.
HOW = {
    "filter_added": "Gmail > Settings > See all settings > Filters and blocked addresses > tick the rule > Delete.",
    "filter_ask": "Owner: Gmail > Settings > See all settings > Filters and blocked addresses. If you don't recognise the newest rule, tap No, remove it.",
    "forwarding_added": "Gmail > Settings > See all settings > Forwarding and POP/IMAP > remove any address you don't recognise > Save.",
    "autoforward_on": "Gmail > Settings > See all settings > Forwarding and POP/IMAP > Disable forwarding > Save changes.",
    "sendas_added": "Gmail > Settings > See all settings > Accounts > Send mail as > delete the address you don't know.",
    "mail_download_on": "Gmail > Settings > See all settings > Forwarding and POP/IMAP > Disable POP and Disable IMAP > Save Changes. Then change the password from your phone.",
    "file_public": "Drive > right-click the folder > Share > General access > Restricted.",
    "heartbeat_missing": "Don't restart the PC. Call your IT helper and say the safety check stopped.",
    "agent_stopping": "Ask at the front desk if anyone switched off Sahayak's protection. If not, don't use the PC and call your IT helper.",
    "backup_old": "Copy the clinic files folder to the backup drive (or ask your IT helper). Do it every week.",
    "pc_health": "On the front-desk PC: Start > Settings > Windows Update > Check for updates. Then open Windows Security and check virus protection is on. Or ask your IT helper.",
}

WHY = {
    "filter_added": "A hidden rule quietly copies or deletes your emails. Criminals use it to watch your invoices and send fake bank details to your vendors.",
    "filter_ask": "Email rules can sort mail, but criminals use them to hide or copy bills. This one looked a little unusual, so only the owner can say if it's theirs.",
    "ransomware_suspected": "Ransomware locks your files and asks for money. Cutting the PC off stops it reaching your other computers.",
    "bank_change_request": "Fraudsters copy a vendor's email and ask you to pay a new account. One call to the number you already have stops it.",
    "mail_download_on": "With this on, a mail program can quietly download every email, bills and patient letters too, and keep a copy even after you change the password.",
    "honeytoken_hit": "We hid a fake bank login in your files. Only an intruder would open it.",
    "agent_stopping": "Attackers often switch off protection first, so nothing warns you while they lock your files.",
    "backup_old": "A recent copy of your files means locked files can simply be put back, without paying anyone.",
    "pc_health": "Most attacks use old weak spots that updates have already fixed. Updates and virus protection close them.",
    "_default": "Someone may be inside your clinic's accounts. Following the steps keeps your money and patient data safe.",
}

ACK_TEXT = "Thank you. Leave it on. Your IT helper will take it from here."
RESTORE_OFFER = "The PC is back online. Do you want us to put the locked files back from the backup?"

# Whole words or word starts only, so "report", "important" and "support" don't trip "port".
JARGON = ["ip address", "ip", "port", "ports", "mac address", "dns", "malware", "payload", "oauth", "api",
          "hash", "entropy", "exploit", "mitre", "endpoint", "firewall", "token", "smtp", "nftables",
          "host", "isolated", "credential", "exfiltrat", "heartbeat", "t1114", "t1486", "t1078", "malicious"]
_JARGON_RE = re.compile(r"\b(" + "|".join(re.escape(w) for w in JARGON) + r")\b", re.I)
_PREFIX_RE = re.compile(r"\b(exfiltrat\w*|credential\w*)", re.I)
MAX_LINES, MAX_CHARS = 3, 330


def jargon_found(text):
    return sorted({m.group(1).lower() for m in _JARGON_RE.finditer(text)} |
                  {m.group(1).lower() for m in _PREFIX_RE.finditer(text)})


def jargon_ok(text):
    lines = [l for l in text.strip().splitlines() if l.strip()]
    return 0 < len(lines) <= MAX_LINES and len(text) <= MAX_CHARS and not jargon_found(text)


def template_for(signal_type, lang="en"):
    t = TEMPLATES.get(signal_type, TEMPLATES["unknown"])
    return t.get(lang) or t["en"]
