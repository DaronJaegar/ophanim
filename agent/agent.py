"""The PC agent (Ayan, Module C). Runs on Priya's front-desk PC.
Run (Linux, real containment needs root):  sudo -E .venv/bin/python -m agent.agent
"""
import os, shutil, signal, sys, threading, time, requests
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from common.config import BRAIN_URL, DEVICE_ID, WATCH_DIR, AGENT_TOKEN, SUSPEND, SIGNAL_METER
from common.contracts import make_event
from agent.detector import Detector, plant_decoys
from agent.fake_ransomware import MARKER
from agent.upgrades import top_writer_now, backup_age_days
from agent import contain as C

AUTO_CONTAIN = True          # owner pre-approved: ransomware is the ONE thing we act on without a tap
BACKUP_DIR = WATCH_DIR.rstrip("/\\") + "_backup"
OLD_BACKUP_DAYS = 7
HEADERS = {"X-Agent-Token": AGENT_TOKEN} if AGENT_TOKEN else {}
state = {"contained": False, "suspended": None, "backup_age_days": None, "restoring": False, "token_warned": False}

def post(path, body):
    try:
        r = requests.post(BRAIN_URL + path, json=body, headers=HEADERS, timeout=3)
        if r.status_code == 401 and not state["token_warned"]:
            state["token_warned"] = True
            print("\nBrain refused the agent token: set the same AGENT_TOKEN in both .env files.")
    except requests.RequestException:
        pass                 # brain unreachable (offline / contained): containment already happened locally

def suspend_writer():
    """Level 3: freeze (not kill) the process writing the most right now, so nothing is lost if we picked wrong."""
    try:
        p = top_writer_now()
        if p:
            p.suspend()
            return {"name": p.name(), "pid": p.pid}
    except Exception as e:                            # psutil.AccessDenied, process already gone...
        print("\ncould not suspend the writing process:", e)
    return None

class Handler(FileSystemEventHandler):
    def __init__(self, det):
        self.det = det
    def _handle(self, kind, path, dest=None):
        if not state["restoring"] and self.det.on_event(kind, path, dest):
            fire(self.det)
    def on_modified(self, e):
        if not e.is_directory: self._handle("modified", e.src_path)
    def on_created(self, e):
        if not e.is_directory: self._handle("created", e.src_path)
    def on_moved(self, e):
        if not e.is_directory: self._handle("moved", e.src_path, e.dest_path)

def fire(det):
    t0 = time.time()
    if AUTO_CONTAIN:
        print()                                       # leave the signal meter's line
        C.contain()                                   # 1. contain first, locally (works offline)
        state["contained"] = True
    seconds = round(time.time() - t0, 2)
    state["suspended"] = suspend_writer() if SUSPEND else None   # 2. freeze the writer (takes ~1 s to sample)
    s = state["suspended"]
    post("/events", make_event("agent", "ransomware_suspected", f"device:{DEVICE_ID}",
                               {"signals": det.active(), "contained": state["contained"],
                                "seconds_to_contain": seconds,
                                "suspended_process": s and s["name"], "suspended_pid": s and s["pid"],
                                "backup_age_days": state["backup_age_days"]}))
    print("\nRANSOMWARE RULE FIRED - contained:", state["contained"],
          "- suspended:", f"{s['name']} (pid {s['pid']})" if s else "nothing")

def restore_files(det):
    """Demo recovery: copy the backup over the locked test folder. Refuses unless the backup is the
    marked test folder, so it can never overwrite a real clinic folder. Returns the files restored."""
    if not os.path.exists(os.path.join(BACKUP_DIR, MARKER)):
        print(f"\nRefusing to restore: {BACKUP_DIR} is not the marked test backup.")
        return 0
    state["restoring"] = True                         # our own copying must not look like an attack
    try:
        for name in os.listdir(WATCH_DIR):            # empty the folder but keep it, so the watcher keeps working
            p = os.path.join(WATCH_DIR, name)
            shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
        shutil.copytree(BACKUP_DIR, WATCH_DIR, dirs_exist_ok=True)
        plant_decoys(WATCH_DIR)
        time.sleep(1)                                 # let the watcher drain the copy events
    finally:
        det.reset()
        state["restoring"] = False
    n = sum(len(files) for _, _, files in os.walk(WATCH_DIR))
    print(f"\nRestored {n} files from {BACKUP_DIR}")
    return n

def heartbeat_loop():
    while True:
        post("/heartbeat", {"device": DEVICE_ID})
        time.sleep(5)

def command_loop(det):
    """The brain never connects in; the agent asks every 3 s whether there is a command for it."""
    while True:
        try:
            cmds = requests.get(f"{BRAIN_URL}/agent/commands", params={"device": DEVICE_ID},
                                headers=HEADERS, timeout=3).json().get("commands", [])
            for c in cmds:
                if c == "release" and state["contained"]:
                    print(); C.release(); state["contained"] = False; det.reset()
                    print("Released by owner")
                elif c == "contain" and not state["contained"]:
                    print(); C.contain(); state["contained"] = True
                elif c == "restore":
                    n = restore_files(det)
                    post("/events", make_event("agent", "files_restored", f"device:{DEVICE_ID}",
                                               {"files": n, "from": BACKUP_DIR, "ok": n > 0}))
        except (requests.RequestException, ValueError):
            pass
        time.sleep(3)

def meter_loop(det):
    """Live signal meter: three dots, so judges watch 1 signal, then 2 -> fired."""
    try:                                              # some Windows consoles can't print the dots
        "●○".encode(sys.stdout.encoding or "ascii")
        on, off = "\033[91m●\033[0m", "\033[2m○\033[0m"
    except (UnicodeEncodeError, LookupError):
        on, off = "[X]", "[ ]"
    while True:
        a, c = det.active(), det.counts()
        rename = f"rename {c['rename']}/20" + (f" (+{c['extension']} odd ext)" if c["extension"] else "")
        parts = [f"{on if a['decoy'] else off} decoy", f"{on if a['entropy'] else off} random writes {c['entropy']}/5",
                 f"{on if a['rename'] else off} {rename}"]
        status = "CONTAINED" if state["contained"] else ("FIRED" if det.fired else "watching")
        sys.stdout.write("\r" + "   ".join(parts) + f"   [{status}]   ")
        sys.stdout.flush()
        time.sleep(1)

def check_backup():
    """At start-up: how old is the newest backup? Older than a week -> tell the brain."""
    age = backup_age_days(BACKUP_DIR) if os.path.isdir(BACKUP_DIR) else None
    state["backup_age_days"] = age
    if age is None:
        print(f"No backup found at {BACKUP_DIR}")
    else:
        print(f"Newest backup: {'today' if age < 1 else f'{age} days old'} ({BACKUP_DIR})")
    if age is None or age > OLD_BACKUP_DAYS:
        post("/events", make_event("agent", "backup_old", f"backup:{DEVICE_ID}",
                                   {"backup_age_days": age, "folder": BACKUP_DIR}))

def main():
    os.makedirs(WATCH_DIR, exist_ok=True)
    plant_decoys(WATCH_DIR)
    det = Detector()
    obs = Observer()
    obs.schedule(Handler(det), WATCH_DIR, recursive=True)
    obs.start()
    check_backup()
    threading.Thread(target=heartbeat_loop, daemon=True).start()
    threading.Thread(target=command_loop, args=(det,), daemon=True).start()
    print(f"Agent watching {WATCH_DIR} as {DEVICE_ID} -> {BRAIN_URL}"
          f"{' (agent token on)' if AGENT_TOKEN else ''}{' (suspend on)' if SUSPEND else ''}")
    if SIGNAL_METER:
        threading.Thread(target=meter_loop, args=(det,), daemon=True).start()
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))   # 'systemctl stop' / kill -> same tamper alarm as Ctrl+C
    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        # Tamper alarm: a normal stop says so at once; a hard kill is caught by the missing heartbeat.
        post("/events", make_event("agent", "agent_stopping", f"device:{DEVICE_ID}", {"contained": state["contained"]}))
        print("\nAgent stopped (brain told)")
        obs.stop(); obs.join()

if __name__ == "__main__":
    main()
