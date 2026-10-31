"""The PC agent (Ayan, Module C). Runs on Priya's front-desk PC.
Run (Linux, real containment needs root):  sudo -E python -m agent.agent
"""
import os, threading, time, requests, psutil
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from common.config import BRAIN_URL, DEVICE_ID, WATCH_DIR
from common.contracts import make_event
from agent.detector import Detector, plant_decoys
from agent import contain as C

AUTO_CONTAIN = True          # owner pre-approved: ransomware is the ONE thing we act on without a tap
state = {"contained": False}

def post(path, body):
    try:
        requests.post(BRAIN_URL + path, json=body, timeout=3)
    except requests.RequestException:
        pass                 # brain unreachable (offline / contained): containment already happened locally

def top_writer():
    """Best guess at the process doing the damage: most bytes written recently (needs psutil + rights)."""
    best = None
    for p in psutil.process_iter(["pid", "name"]):
        try:
            io = p.io_counters()
            if best is None or io.write_bytes > best[1]:
                best = (p, io.write_bytes)
        except (psutil.Error, AttributeError):
            continue
    return best[0] if best else None

class Handler(FileSystemEventHandler):
    def __init__(self, det):
        self.det = det
    def _handle(self, kind, path, dest=None):
        if self.det.on_event(kind, path, dest):
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
        C.contain()                                   # 1. contain first, locally (works offline)
        state["contained"] = True
    suspended = None
    # Level 3: uncomment to freeze the process doing the writing
    # p = top_writer(); p and p.suspend(); suspended = p and p.name()
    post("/events", make_event("agent", "ransomware_suspected", f"device:{DEVICE_ID}",
                               {"signals": det.active(), "contained": state["contained"],
                                "seconds_to_contain": round(time.time() - t0, 2),
                                "suspended_process": suspended}))
    print("RANSOMWARE RULE FIRED - contained:", state["contained"])

def heartbeat_loop():
    while True:
        post("/heartbeat", {"device": DEVICE_ID})
        time.sleep(5)

def command_loop(det):
    """The brain never connects in; the agent asks every 3 s whether there is a command for it."""
    while True:
        try:
            cmds = requests.get(f"{BRAIN_URL}/agent/commands", params={"device": DEVICE_ID}, timeout=3).json()["commands"]
            for c in cmds:
                if c == "release" and state["contained"]:
                    C.release(); state["contained"] = False; det.fired = False
                    print("Released by owner")
                elif c == "contain" and not state["contained"]:
                    C.contain(); state["contained"] = True
        except requests.RequestException:
            pass
        time.sleep(3)

def main():
    os.makedirs(WATCH_DIR, exist_ok=True)
    plant_decoys(WATCH_DIR)
    det = Detector()
    obs = Observer()
    obs.schedule(Handler(det), WATCH_DIR, recursive=True)
    obs.start()
    threading.Thread(target=heartbeat_loop, daemon=True).start()
    threading.Thread(target=command_loop, args=(det,), daemon=True).start()
    print(f"Agent watching {WATCH_DIR} as {DEVICE_ID} -> {BRAIN_URL}")
    try:
        while True:
            time.sleep(1)
    finally:
        obs.stop(); obs.join()

if __name__ == "__main__":
    main()
