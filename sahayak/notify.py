"""Send an incident to staff and owner with signed buttons (Aradhya, Module D).
The brain calls send_incident(incident) whenever an incident opens or changes."""
import requests
from common.config import TELEGRAM_TOKEN, OWNER_CHAT_ID, STAFF_CHAT_IDS, SECURITY_CODE, CHAT_LANGS
from sahayak import signing
from sahayak.messages import template_for, STEP_TEXT
from sahayak.llm import reword

LANG = CHAT_LANGS   # chat_id -> "en" | "hi" | "kn"  (from CHAT_LANGS in .env)

BUTTONS = {          # signal type -> [(label, code)]; codes are decoded by the bot
    "filter_added": [("Remove it", "rm"), ("Call my IT helper", "it"), ("What does this mean?", "why")],
    "forwarding_added": [("Show me how to stop it", "how"), ("Call my IT helper", "it")],
    "autoforward_on": [("Show me how to turn it off", "how"), ("Call my IT helper", "it")],
    "sendas_added": [("Show me how to remove it", "how"), ("Call my IT helper", "it")],
    "file_public": [("Make it private", "mp"), ("Call my IT helper", "it")],
    "honeytoken_hit": [("Start the fix", "st"), ("Call my IT helper", "it")],
    "ransomware_suspected": [("Okay, I won't switch it off", "ack"), ("Call my IT helper", "it")],
    "heartbeat_missing": [("Call my IT helper", "it")],
    "bank_change_request": [("Check with the vendor", "vv")],
}

def _send(chat_id, text, buttons):
    kb = {"inline_keyboard": [[{"text": label, "callback_data": data}] for label, data in buttons]}
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                  json={"chat_id": chat_id, "text": text, "reply_markup": kb}, timeout=10)

def render(inc, lang="en"):
    merged = len(inc.get("kinds", [])) > 1
    stype = "merged" if merged else inc["signals"][-1]["type"]
    body = template_for(stype, lang)
    if lang == "en":
        body = reword(body, {"title": inc["title"], "severity": inc["severity"]})
    head = f"Sahayak · Code {SECURITY_CODE}\n"
    return head + body, stype

def buttons_for(inc, stype, is_owner):
    iid = inc["id"]
    if stype == "merged":
        todo = [s for s in inc["runbook"] if s not in inc.get("done", [])]
        out = [(f"Done: {STEP_TEXT[todo[0]][:40]}", f"sd{inc['runbook'].index(todo[0])}")] if todo else []
        if is_owner and "contain_pc" in inc["runbook"]:
            out.append(("Owner: release the PC", "rel"))
    else:
        out = list(BUTTONS.get(stype, []))
        if is_owner and stype == "ransomware_suspected":
            out.append(("Owner: release the PC", "rel"))
    return [(label, signing.make(iid, code)) for label, code in out]

def send_incident(inc):
    if not TELEGRAM_TOKEN:
        print("[Sahayak] would send:", inc["title"]); return
    for chat in [OWNER_CHAT_ID] + STAFF_CHAT_IDS:
        if not chat:
            continue
        text, stype = render(inc, LANG.get(chat, "en"))
        _send(chat, text, buttons_for(inc, stype, chat == OWNER_CHAT_ID))
