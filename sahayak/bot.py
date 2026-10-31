"""Sahayak bot (Aradhya, Module D): receives taps and messages from staff.
Run ONE copy only:  python -m sahayak.bot
"""
import asyncio, re, requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from common.config import (TELEGRAM_TOKEN, OWNER_CHAT_ID, STAFF_CHAT_IDS, VENDOR_CHAT_IDS, BRAIN_URL,
                           SECURITY_CODE, IT_CHAT_ID, CLINIC_NAME, brain_headers)
from common.contracts import make_event
from sahayak import ask, signing
from sahayak.messages import STEP_TEXT, STEP_HOW, STEP_DONE, OWNER_STEPS, HOW, WHY, ACK_TEXT, RESTORE_OFFER
from sahayak.notify import header, incident_type

ALLOWED = {c for c in [OWNER_CHAT_ID] + STAFF_CHAT_IDS if c}
VENDOR_CHATS = set(VENDOR_CHAT_IDS.values())
VENDOR_CODES = {"vy", "vn"}
OWNER_ONLY = {"rel", "rs", "mine"}
ACTIONS = {"rm": "remove_filter", "mp": "make_private", "rel": "release_pc", "rs": "restore_files",
           "mine": "rule_is_mine"}
DONE_TEXT = {        # code -> (worked, didn't work)
    "rm": ("We checked: it's gone.", "We couldn't remove it automatically. Tap Show me how, or call your IT helper."),
    "mp": ("We checked: only your clinic can open it now.", "We couldn't change it automatically. Your IT helper has the details."),
    "rel": ("The PC is being reconnected.", "The PC is still cut off. Your IT helper has the details."),
    "rs": ("We're putting the files back from the backup. It takes about a minute.",
           "We couldn't start putting the files back. Your IT helper has the details."),
    "mine": ("We'll leave your rule alone and won't ask about it again.",
             "We couldn't save your answer. Your IT helper has the details."),
}
SUCCESS = {"rm": "removed", "mp": "made_private", "rel": "ok", "rs": "queued", "mine": "confirmed"}
PAISA_ENTITY = "vendor:payment"   # its own entity, so Paisa Pause never merges into the email/PC incident
BANK_CHANGE = re.compile(r"(bank|account|a/c|ifsc|upi).{0,40}(chang|new|updat)|"
                         r"(chang|new|updat).{0,40}(bank|account|a/c|ifsc|upi)", re.I | re.S)
NO_BRAIN = "I can't reach the safety system right now. Please call your IT helper."


class Refused(Exception):
    pass


def check_tap(cid, data):
    """Every safety check for a button tap. Returns (incident_id, code) or raises Refused."""
    try:
        iid, code = signing.verify(data)                          # 1. signature, expiry, one-time
    except signing.BadTap as e:
        raise Refused(f"Rejected: {e}")
    if code in VENDOR_CODES:                                       # 2. only the vendor answers the vendor question
        if cid not in VENDOR_CHATS:
            raise Refused("Only the vendor can answer this.")
    elif cid not in ALLOWED:                                       # 3. only clinic phones act
        raise Refused("This phone is not allowed to act.")
    if code in OWNER_ONLY and cid != OWNER_CHAT_ID:                # 4. roles
        raise Refused("Only the owner can do this.")
    return iid, code


# ---------- talking to the brain (in a thread, so one slow call never freezes every chat) ----------
async def brain(path, body):
    def go():
        r = requests.post(BRAIN_URL + path, json=body, headers=brain_headers(), timeout=10)
        try:
            return r.json() if r.content else {}
        except ValueError:
            return {"detail": r.text[:200]}
    return await asyncio.to_thread(go)


async def get_incident(iid):
    incs = await asyncio.to_thread(lambda: requests.get(BRAIN_URL + "/incidents", timeout=10).json())
    return next((i for i in incs if i.get("id") == iid), None)


FAKE_INVOICE = "FAKE INVOICE: the vendor did not send this. Do not pay."


def filter_incident(incs):
    """Latest open incident that still holds an attacker email rule (so Remove it has something to delete)."""
    found = [i for i in incs or []
             if i.get("status") == "open" and "remove_attacker_rules" not in (i.get("done") or [])
             and any((s.get("evidence") or {}).get("filter") for s in i.get("signals") or [])]
    return max(found, key=lambda i: str(i.get("updated", "")), default=None)


def fake_invoice_followup(incs, paisa_iid):
    """What the owner gets after the vendor says No: (text, [(label, signed callback)]).
    Remove it is offered only when an open incident really has an email rule to delete, and is signed
    for THAT incident; otherwise only Call my IT helper, so we never show a button that would fail."""
    inc = filter_incident(incs)
    if inc:
        text = (f"{FAKE_INVOICE}\nA hidden email rule may be showing your invoices to the scammer.\n"
                "Tap Remove it.")
        return text, [("Remove it", signing.make(inc["id"], "rm")), ("Call my IT helper", signing.make(inc["id"], "it"))]
    text = f"{FAKE_INVOICE}\nYour IT helper can check if someone is reading your email."
    return text, [("Call my IT helper", signing.make(paisa_iid, "it"))]


def it_summary(inc):
    """The IT helper's view: markers, points and MITRE from our own fields (ask.explain_incident), never raw
    filter text or addresses (attacker-written). The full evidence is in the brain's report page."""
    if not inc.get("signals"):
        return f"Alert {inc.get('id', '?')}: the details could not be loaded. Check {BRAIN_URL}/console"
    return (ask.explain_incident(inc, mode="it") +
            f"\n\nFull report with the evidence: {BRAIN_URL}/incidents/{inc.get('id')}/report")


async def send_to_it(ctx, inc):
    """The technical view goes to the IT helper (jargon allowed here). Returns True if sent."""
    if not IT_CHAT_ID:
        return False
    await ctx.bot.send_message(IT_CHAT_ID, f"{header()} · technical details for the IT helper\n{it_summary(inc)[:3800]}")
    return True


# ---------- commands ----------
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cid = str(update.effective_chat.id)
    role = ("owner" if cid == OWNER_CHAT_ID else "staff" if cid in ALLOWED else
            "vendor" if cid in VENDOR_CHATS else "IT helper" if cid == IT_CHAT_ID else "not set up yet")
    await update.message.reply_text(
        f"Namaste! I am Sahayak, {CLINIC_NAME}'s safety helper.\n"
        f"Your chat id is {cid} (role: {role}).\n"
        f"Every real message from me starts with the code {SECURITY_CODE}. "
        "I will never ask for passwords, OTPs or payments. No code? Not us.")


# ---------- button taps ----------
async def on_button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    cid = str(q.message.chat.id)
    try:
        iid, code = check_tap(cid, q.data)
    except Refused as e:
        await q.answer(str(e), show_alert=True)
        return
    await q.answer()
    try:
        await handle(q, ctx, cid, iid, code)
    except (requests.RequestException, ValueError):
        await q.message.reply_text(NO_BRAIN)


async def handle(q, ctx, cid, iid, code):
    if code in ACTIONS:
        res = await brain("/actions", {"incident_id": iid, "action": ACTIONS[code], "by": cid})
        good, bad = DONE_TEXT[code]
        await q.edit_message_text(q.message.text + "\n\n" + (("Done. " + good) if res.get(SUCCESS[code]) else bad))
        if code == "rel" and res.get(SUCCESS[code]):              # recovery: offer the backup once the PC is back
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("Owner: put the files back",
                                                             callback_data=signing.make(iid, "rs"))]])
            await q.message.reply_text(f"{header()}\n{RESTORE_OFFER}", reply_markup=kb)

    elif code.startswith("sd"):                                   # a runbook step is done
        inc = await get_incident(iid)
        if not inc:
            await q.message.reply_text(NO_BRAIN); return
        step = inc["runbook"][int(code[2:])]
        if step in inc.get("done", []):
            await q.message.reply_text("That step is already done."); return
        if step in OWNER_STEPS and cid != OWNER_CHAT_ID:
            await q.message.reply_text("Only the owner can confirm this step."); return
        res = await brain("/actions", {"incident_id": iid, "action": "step_done", "step": step, "by": cid})
        extra = ""
        if step == "remove_attacker_rules":
            extra = " We checked: they're gone." if res.get("removed") else " Your IT helper will check they're gone."
        if step == "report" and await send_to_it(ctx, inc):
            extra = " Report sent."
        await q.edit_message_text(q.message.text + f"\n\n✔ {STEP_DONE.get(step, step)}.{extra}")
        # the brain re-sends the incident, so the next "Done" button arrives by itself

    elif code == "st":                                            # numbered steps, in order
        inc = await get_incident(iid) or {}
        steps = inc.get("runbook") or []
        await q.message.reply_text("Do these one at a time:\n" + "\n".join(
            f"{n}. {STEP_TEXT.get(s, s)}" for n, s in enumerate(steps, 1)) if steps else "Your IT helper will guide you.")

    elif code == "how":
        inc = await get_incident(iid) or {}
        stype = incident_type(inc) if inc else "unknown"
        if stype == "merged":
            todo = [s for s in inc.get("runbook", []) if s not in inc.get("done", [])]
            text = STEP_HOW.get(todo[0], STEP_TEXT.get(todo[0], "")) if todo else "All steps are done."
        else:
            text = HOW.get(stype, "Your IT helper will guide you.")
        await q.message.reply_text(text)

    elif code == "why":
        inc = await get_incident(iid) or {}
        await q.message.reply_text(WHY.get(incident_type(inc) if inc else "", WHY["_default"]))

    elif code == "it":
        await brain("/actions", {"incident_id": iid, "action": "called_it_helper", "by": cid})   # stops reminders
        inc = await get_incident(iid) or {"id": iid}
        if await send_to_it(ctx, inc):
            await q.message.reply_text("We've sent your IT helper the details. They'll call you.")
        else:
            await q.message.reply_text(f"Please call your IT helper and say: 'Sahayak alert number {iid}'.")

    elif code == "ack":
        await brain("/actions", {"incident_id": iid, "action": "ack", "by": cid})   # recorded in the audit log
        await q.edit_message_text(q.message.text + "\n\n" + ACK_TEXT)

    elif code == "vv":                                            # Paisa Pause: ask the vendor
        await brain("/actions", {"incident_id": iid, "action": "asked_vendor", "by": cid})       # stops reminders
        if not VENDOR_CHAT_IDS:
            await q.message.reply_text("Don't pay. Call the vendor on the number you already have, "
                                       "not the one in the message."); return
        for name, vchat in VENDOR_CHAT_IDS.items():               # demo: every saved vendor; real: match the name
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("Yes, I sent it", callback_data=signing.make(iid, "vy"))],
                [InlineKeyboardButton("No, not me", callback_data=signing.make(iid, "vn"))]])
            await ctx.bot.send_message(vchat, f"{CLINIC_NAME} received a message saying the bank details for "
                                              f"{name} changed. Did you send it?", reply_markup=kb)
        await q.edit_message_text(q.message.text + "\n\nWe've asked the vendor on the number you saved. "
                                  "Don't pay until they reply.")

    elif code in VENDOR_CODES:
        if code == "vy":
            await ctx.bot.send_message(OWNER_CHAT_ID, f"{header()}\n"
                                       "The vendor confirmed the change. You can pay the new account.")
        else:
            try:
                incs = await asyncio.to_thread(lambda: requests.get(BRAIN_URL + "/incidents", timeout=10).json())
            except (requests.RequestException, ValueError):
                incs = []                                         # no brain: still warn, just no Remove it
            text, buttons = fake_invoice_followup(incs, iid)
            kb = InlineKeyboardMarkup([[InlineKeyboardButton(label, callback_data=data)] for label, data in buttons])
            await ctx.bot.send_message(OWNER_CHAT_ID, f"{header()}\n{text}", reply_markup=kb)
        try:
            await brain("/actions", {"incident_id": iid, "by": cid,
                                     "action": "vendor_said_yes" if code == "vy" else "vendor_said_no"})
        except requests.RequestException:
            pass                                                  # the owner already has the verdict
        await q.edit_message_text("Thank you, the clinic has been told.")


# ---------- Ask Sahayak: questions in plain words, answered from our guides ----------
HELP_TEXT = ("Ask me anything about the clinic's safety in your own words, even with spelling mistakes. For example:\n"
             "• what do I do now?\n• someone wants the OTP, should I give it?\n• is this bill real?\n"
             "• the computer is showing strange pop-ups\n"
             "Say \"steps\" for step-by-step help, or \"didn't understand\" for simpler words.\n"
             "Forward any message about changed bank details and I'll check it with the vendor.\n"
             "I never ask for passwords, OTPs or payments.")


def route(cid, text, is_forward=False, has_photo=False):
    """Where a message goes: 'paisa' | 'photo_hint' | 'not_bank' | 'ask' | 'ignore'.
    Paisa Pause first; a forwarded message is something to check, not a question."""
    clinic, it = cid in ALLOWED, bool(IT_CHAT_ID) and cid == IT_CHAT_ID
    if clinic and BANK_CHANGE.search(text or ""):
        return "paisa"
    if clinic and has_photo and not text:
        return "photo_hint"
    if clinic and is_forward:
        return "not_bank"
    if (clinic or it) and (text or "").strip():
        return "ask"
    return "ignore"


async def reply_ask(update: Update, ctx: ContextTypes.DEFAULT_TYPE, question):
    cid = str(update.effective_chat.id)
    mode = "it" if IT_CHAT_ID and cid == IT_CHAT_ID else "staff"
    try:
        await ctx.bot.send_chat_action(update.effective_chat.id, "typing")
    except Exception:
        pass
    try:
        incs = await asyncio.to_thread(lambda: requests.get(BRAIN_URL + "/incidents", timeout=5).json())
    except (requests.RequestException, ValueError):
        incs = []                                                 # no brain: answer from the guides alone
    text, source, _ = await asyncio.to_thread(ask.answer, question, incs, mode, None, cid)
    tail = f"\n\n(From our guide: {source})" if source else ""
    await update.message.reply_text(f"{header()}\n{text}{tail}")


async def ask_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cid = str(update.effective_chat.id)
    if cid not in ALLOWED and not (IT_CHAT_ID and cid == IT_CHAT_ID):
        return
    question = " ".join(ctx.args or [])
    if not question:
        await update.message.reply_text("Type your question after /ask, for example: /ask what do I do now?")
        return
    await reply_ask(update, ctx, question)


def status_text(incs, mode="staff"):
    """/status gives the same answer as asking "is everything ok?" (ask.open_incident / SYSTEM_OK)."""
    live = ask.open_incident(incs)
    if not live:
        return ask.SYSTEM_OK
    others = sum(1 for i in incs if i.get("status") == "open") - 1
    more = f"\n\n{others} other alert(s) are also open." if others > 0 else ""
    return ask.explain_incident(live, mode) + more


async def status_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cid = str(update.effective_chat.id)
    if cid not in ALLOWED and not (IT_CHAT_ID and cid == IT_CHAT_ID):
        return
    try:
        incs = await asyncio.to_thread(lambda: requests.get(BRAIN_URL + "/incidents", timeout=5).json())
    except (requests.RequestException, ValueError):
        await update.message.reply_text(NO_BRAIN); return
    mode = "it" if IT_CHAT_ID and cid == IT_CHAT_ID else "staff"
    await update.message.reply_text(f"{header()}\n{status_text(incs, mode)}"[:4000])


def digest_text(d):
    """/digest: small email rule changes that did not need an alert. Counts and our own labels only."""
    n = d.get("count", 0)
    if not n:
        return "No small email rule changes since the safety check started. Nothing to look at."
    lines = [f"{n} small email rule change(s) looked normal, so we didn't send an alert.",
             "What we noticed:"] + [f"• {m}: {c}" for m, c in sorted(d.get("by_marker", {}).items())]
    lines.append("If nobody at the clinic made new email rules, tap /status or call your IT helper.")
    return "\n".join(lines)


async def digest_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cid = str(update.effective_chat.id)
    if cid not in ALLOWED and not (IT_CHAT_ID and cid == IT_CHAT_ID):
        return
    try:
        d = await asyncio.to_thread(lambda: requests.get(BRAIN_URL + "/digest", timeout=5).json())
    except (requests.RequestException, ValueError):
        await update.message.reply_text(NO_BRAIN); return
    await update.message.reply_text(f"{header()}\n{digest_text(d)}")


async def help_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"{header()}\n{HELP_TEXT}")


# ---------- forwarded messages, invoice photos (Paisa Pause) and questions ----------
async def on_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cid = str(update.effective_chat.id)
    text = update.message.text or update.message.caption or ""
    where = route(cid, text, is_forward=getattr(update.message, "forward_origin", None) is not None,
                  has_photo=bool(update.message.photo))
    if where == "ask":
        await reply_ask(update, ctx, text)
        return
    if where == "ignore":
        return                                                    # only clinic phones (and IT) are answered
    if where == "paisa":
        try:
            await brain("/events", make_event("sahayak", "bank_change_request", PAISA_ENTITY, {"text": text[:500]}))
            # the brain opens an incident and calls notify.send_incident -> "Don't pay yet" arrives
        except requests.RequestException:
            await update.message.reply_text(f"{header()}\nDon't pay yet. Call the vendor on the number "
                                            "you already have, not the one in this message.")
    elif where == "photo_hint":
        await update.message.reply_text("If this invoice says the bank details changed, send the photo again "
                                        "with a caption like 'bank details changed'.")
    else:
        await update.message.reply_text("Thanks. I don't see a bank-detail change in this message. "
                                        "You can also ask me a question in your own words.")


def main():
    if not TELEGRAM_TOKEN:
        raise SystemExit("Put TELEGRAM_TOKEN in .env first (from @BotFather).")
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ask", ask_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("digest", digest_command))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler((filters.TEXT & ~filters.COMMAND) | filters.PHOTO, on_text))
    print(f"Sahayak running. owner={OWNER_CHAT_ID or '-'} staff={STAFF_CHAT_IDS} "
          f"vendors={list(VENDOR_CHAT_IDS)} IT={IT_CHAT_ID or '-'} brain={BRAIN_URL}")
    app.run_polling()


if __name__ == "__main__":
    main()
