"""Sahayak bot (Aradhya, Module D): receives taps and messages from staff.
Run:  python -m sahayak.bot
"""
import asyncio, re, requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from common.config import TELEGRAM_TOKEN, OWNER_CHAT_ID, STAFF_CHAT_IDS, VENDOR_CHAT_IDS, BRAIN_URL, SECURITY_CODE
from common.contracts import make_event
from sahayak import signing
from sahayak.messages import STEP_TEXT

ALLOWED = {c for c in [OWNER_CHAT_ID] + STAFF_CHAT_IDS if c}
OWNER_ONLY = {"rel"}
ACTIONS = {"rm": "remove_filter", "mp": "make_private", "rel": "release_pc"}
HOW_TO = ("Open Gmail on your phone > Settings > See all settings > 'Forwarding and POP/IMAP'.\n"
          "Remove any address you don't recognise, then tap Save.")
WHY = ("A hidden rule quietly copies or deletes your emails. Criminals use it to watch your invoices "
       "and send fake bank details to your vendors.")
BANK_CHANGE = re.compile(r"(bank|account|a/c|ifsc|upi).{0,40}(chang|new|updat)|(chang|new|updat).{0,40}(bank|account|a/c|ifsc|upi)", re.I)

async def brain(path, body):
    return await asyncio.to_thread(lambda: requests.post(BRAIN_URL + path, json=body, timeout=10).json())

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cid = str(update.effective_chat.id)
    await update.message.reply_text(
        f"Namaste! I am Sahayak. Your chat id is {cid}.\n"
        f"Every real message from me starts with the code {SECURITY_CODE}. I will never ask for passwords, OTPs or payments.")

async def on_button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    cid = str(q.message.chat.id)
    try:
        iid, code = signing.verify(q.data)
    except signing.BadTap as e:
        await q.answer(f"Rejected: {e}", show_alert=True); return
    if cid not in ALLOWED and code not in ("vy", "vn"):
        await q.answer("This phone is not allowed to act.", show_alert=True); return
    if code in OWNER_ONLY and cid != OWNER_CHAT_ID:
        await q.answer("Only the owner can do this.", show_alert=True); return
    await q.answer()
    if code in ACTIONS:
        res = await brain("/actions", {"incident_id": iid, "action": ACTIONS[code], "by": cid})
        await q.edit_message_text(q.message.text + "\n\nDone. " + ("We checked: it's gone." if res.get("removed") or res.get("made_private") else "Your IT helper has the details."))
    elif code.startswith("sd"):
        incs = await asyncio.to_thread(lambda: requests.get(BRAIN_URL + "/incidents", timeout=10).json())
        inc = next(i for i in incs if i["id"] == iid)
        step = inc["runbook"][int(code[2:])]
        await brain("/actions", {"incident_id": iid, "action": "step_done", "step": step, "by": cid})
        await q.edit_message_text(q.message.text + f"\n\n✔ {STEP_TEXT[step]}")
    elif code == "st":                                # honeytoken: send the takeover steps in order
        incs = await asyncio.to_thread(lambda: requests.get(BRAIN_URL + "/incidents", timeout=10).json())
        inc = next(i for i in incs if i["id"] == iid)
        await q.message.reply_text("Do these one at a time:\n" + "\n".join(
            f"{n}. {STEP_TEXT[s]}" for n, s in enumerate(inc["runbook"], 1)))
    elif code == "how":
        await q.message.reply_text(HOW_TO)
    elif code == "why":
        await q.message.reply_text(WHY)
    elif code == "it":
        await q.message.reply_text("Your IT helper has been sent the full technical details.")
    elif code == "ack":
        await q.edit_message_text(q.message.text + "\n\nThank you. Leave it on; help is coming.")
    elif code == "vv":
        for name, vchat in VENDOR_CHAT_IDS.items():       # demo: ask every saved vendor; real: match the name
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("Yes, I sent it", callback_data=signing.make(iid, "vy"))],
                                       [InlineKeyboardButton("No, not me", callback_data=signing.make(iid, "vn"))]])
            await ctx.bot.send_message(vchat, f"Sunrise Clinic received a message saying {name}'s bank details changed. Did you send it?", reply_markup=kb)
        await q.message.reply_text("We've asked the vendor on the number you saved. Don't pay until they reply.")
    elif code in ("vy", "vn"):
        verdict = "The vendor confirmed the change." if code == "vy" else "FAKE INVOICE: the vendor did not send this. Do not pay."
        await ctx.bot.send_message(OWNER_CHAT_ID, f"Sahayak · Code {SECURITY_CODE}\n{verdict}")
        await q.edit_message_text("Thank you, the clinic has been told.")

async def on_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Paisa Pause: staff forward a suspicious invoice or message to Sahayak."""
    if str(update.effective_chat.id) not in ALLOWED:
        return                                        # only clinic phones can raise alerts
    text = update.message.text or update.message.caption or ""
    if BANK_CHANGE.search(text):
        await brain("/events", make_event("sahayak", "bank_change_request", "gmail:clinic", {"text": text[:500]}))
    else:
        await update.message.reply_text("Thanks. I don't see a bank-detail change in this message.")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    app.run_polling()

if __name__ == "__main__":
    main()
