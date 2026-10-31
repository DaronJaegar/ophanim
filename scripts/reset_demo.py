"""One-command reset between demo runs (Aaron, Module B). Run on Aaron's laptop, from the project folder,
while the brain is still running (step 1 needs it):
  python -m scripts.reset_demo --dry-run     # show every step, change nothing
  python -m scripts.reset_demo               # asks you to type RESET, then does it
  python -m scripts.reset_demo --no-start    # don't start brain, sensors and bot again afterwards
Steps:
  1 Ayan's PC: release + restore files (owner-only actions, queued through the running brain)
  2 Gmail: delete filters not in gmail_baseline.json (forwarding addresses stay)
  3 Drive: make every "anyone with the link" file private
  4 stop brain, sensors and bot (the graph, recent changes and Ask Sahayak's topic memory live in memory)
  5 move chakravyuh.db to runs/ (earlier audit trails are kept, still git-ignored), clear used button taps
  6 start brain, sensors and bot again, each in its own window
Never touches .env, tokens or forwarding addresses."""
import os, shutil, subprocess, sys, time
from datetime import datetime
import requests

from common.config import BRAIN_URL, OWNER_CHAT_ID, brain_headers

DB, RUNS = "chakravyuh.db", "runs"
PROCESSES = {"brain": "brain.app:app", "sensors": "sensors.run", "bot": "sahayak.bot"}
START = {"brain": ["-m", "uvicorn", "brain.app:app", "--host", "0.0.0.0", "--port", "8000"],
         "sensors": ["-m", "sensors.run"], "bot": ["-m", "sahayak.bot"]}


def pc_actions(incidents):
    """(incident id, action) to undo a ransomware run: release first, then put the files back."""
    return [(i["id"], a) for i in incidents or []
            if i.get("status") == "open" and any(s.get("type") == "ransomware_suspected" for s in i.get("signals") or [])
            for a in ("release_pc", "restore_files")]


def step_pc(dry, http=requests, wait=30):
    try:
        incs = http.get(BRAIN_URL + "/incidents", timeout=5).json()
    except Exception:
        print("1. PC: brain not running, skipped. If Ayan's PC is cut off, run release on it by hand.")
        return
    todo = pc_actions(incs)
    if not todo:
        print("1. PC: no open ransomware incident, nothing to release or restore.")
        return
    for iid, action in todo:
        print(f"1. PC: {action} for incident {iid}" + (" (dry run)" if dry else ""))
        if not dry:
            r = http.post(BRAIN_URL + "/actions", json={"incident_id": iid, "action": action, "by": OWNER_CHAT_ID},
                          headers=brain_headers(), timeout=10)
            print("   ->", r.status_code, r.json() if r.content else "")
    if dry:
        return
    for _ in range(wait // 3):                  # the agent polls every 3 s and reports files_restored when done
        rows = http.get(BRAIN_URL + "/audit", timeout=5).json().get("rows", [])
        if any(r["body"].get("type") == "files_restored" for r in rows):
            print("   files restored on the PC.")
            return
        time.sleep(3)
    print("   no files_restored yet: ask Ayan to check the agent window.")


def step_gmail(dry):
    from sensors import reset_gmail
    print("2. Gmail: filters not in the baseline" + (" (dry run: listed only)" if dry else ""))
    try:
        reset_gmail.main([] if dry else ["--yes"])
    except SystemExit as e:                     # no baseline saved yet
        print("  ", e)


def public_files(svc):
    q = "visibility='anyoneWithLink' or visibility='anyoneCanFind'"
    return svc.files().list(q=q, fields="files(id,name)").execute().get("files", [])


def step_drive(dry, svc=None, fix=None):
    if svc is None:
        from sensors.google_auth import drive
        svc = drive()
    if fix is None:
        from sensors.fixes import make_private as fix
    files = public_files(svc)
    print(f"3. Drive: {len(files)} file(s) open to anyone" + (" (dry run)" if dry and files else ""))
    for f in files:
        print("  ", f["name"])
        if not dry:
            print("   private now:", fix(f["id"], []))     # a folder first makes its files private too


def targets(procs, me=os.getpid()):
    """Our running processes: [(pid, name)]. Matches the module in the command line, never this script."""
    out = []
    for p in procs:
        try:
            cmd = " ".join(p.info.get("cmdline") or [])
        except Exception:
            continue
        for name, needle in PROCESSES.items():
            if needle in cmd and p.info["pid"] != me and "reset_demo" not in cmd:
                out.append((p.info["pid"], name))
    return out


def step_stop(dry):
    import psutil
    found = targets(psutil.process_iter(["pid", "cmdline"]))
    print(f"4. Stop: {sorted({n for _, n in found}) or 'nothing running'}" + (" (dry run)" if dry else ""))
    if dry:
        return
    for pid, _ in found:
        try:
            psutil.Process(pid).kill()
        except psutil.Error:
            pass                                # a venv launcher's child is already gone
    time.sleep(1.5)


def step_db(dry, db=DB, runs=RUNS):
    from sahayak import signing
    if not os.path.exists(db):
        print("5. Audit database: none yet.")
    else:
        dest = os.path.join(runs, f"chakravyuh-{datetime.now():%Y%m%d-%H%M%S}.db")
        print(f"5. Audit database -> {dest}" + (" (dry run)" if dry else ""))
        if not dry:
            os.makedirs(runs, exist_ok=True)
            for _ in range(5):                  # Windows keeps the file locked for a moment after the brain stops
                try:
                    shutil.move(db, dest)
                    break
                except PermissionError:
                    time.sleep(1)
            else:
                raise SystemExit(f"{db} is still in use: stop the brain and run again.")
    print("   used button taps cleared" + (" (dry run)" if dry else ""))
    if not dry:
        signing.reset_used()


def step_start(dry):
    print("6. Start brain, sensors, bot in new windows" + (" (dry run)" if dry else ""))
    if dry:
        return
    flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
    for name in ("brain", "sensors", "bot"):
        subprocess.Popen([sys.executable] + START[name], creationflags=flags)
        time.sleep(4 if name == "brain" else 1)     # sensors and bot need the brain up first
    print("   started. Open http://127.0.0.1:8000/console")


def main(args):
    dry = "--dry-run" in args
    if not dry and input("This resets the demo (Gmail filters, Drive sharing, PC, audit log). Type RESET: ").strip() != "RESET":
        raise SystemExit("Nothing changed.")
    step_pc(dry)
    step_gmail(dry)
    step_drive(dry)
    step_stop(dry)
    step_db(dry)
    if "--no-start" not in args:
        step_start(dry)
    print("Dry run: nothing was changed." if dry else "Reset done.")


if __name__ == "__main__":
    main(sys.argv[1:])
