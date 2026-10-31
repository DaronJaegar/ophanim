"""Checks Bruce's Session 4 list against files on disk and the audit log (read only).
Run from the project folder:  python -m eval.check_session4"""
import json, os, sqlite3

rows = []
if os.path.exists("chakravyuh.db"):
    c = sqlite3.connect("file:chakravyuh.db?mode=ro", uri=True)
    rows = [json.loads(r[0]) for r in c.execute("select body from audit order by id")]

events = lambda t: [r for r in rows if r.get("kind") == "event" and r.get("type") == t]
fixes = [r for r in rows if r.get("kind") == "fix" and r.get("what") == "make_private"]
honey = events("honeytoken_hit")


def show(ok, text):
    print(("[DONE] " if ok else "[ -- ] ") + text)


show(os.path.exists("token_drive_write.json"), "1. Drive write token (token_drive_write.json)")
show(os.path.exists("gmail_baseline.json"), "2. Gmail baseline saved (gmail_baseline.json)")
pub = events("file_public")
show(len(pub) >= 1, f"3a. Drive share alerted (file_public events: {len(pub)})")
show(any(f.get("verified") for f in fixes), f"3b. Make it private worked (verified fixes: {sum(1 for f in fixes if f.get('verified'))})")
first_fix = next((i for i, r in enumerate(rows) if r.get("kind") == "fix" and r.get("what") == "make_private" and r.get("verified")), None)
again = first_fix is not None and any(r.get("kind") == "event" and r.get("type") == "file_public" for r in rows[first_fix:])
show(again, "3c. Re-share alerted again (a file_public event after a verified Make it private)")
show(len(honey) >= 1, f"4a. Decoy link opened in a browser alerted (honeytoken hits: {len(honey)})")
for h in honey[-3:]:
    ev = h.get("evidence", {})
    print(f"       {h.get('ts', '')[:19]}  {ev.get('planted_in')}  {ev.get('user_agent', '')[:60]}")
print("4b. Telegram paste: check that no new honeytoken hit appeared after you pasted the link.")
