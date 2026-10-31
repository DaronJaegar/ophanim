"""Run the watchers and send every change to the brain (Bruce, Module A).
Run:  python -m sensors.run
"""
import time, requests
from common.config import BRAIN_URL, POLL_SECONDS
from common.contracts import make_event
from sensors.google_auth import gmail, drive
from sensors.gmail_watch import snapshot, diff
from sensors.drive_watch import DriveWatcher

def main():
    g = gmail()
    dw = DriveWatcher(drive())
    last = None
    print(f"Watching Gmail + Drive every {POLL_SECONDS}s -> {BRAIN_URL}")
    while True:
        try:
            snap = snapshot(g)
            changes = diff(last, snap)
            if last is None:
                print("Baseline:", len(snap["filters"]), "filters,", len(snap["forwarding"]), "forwarding addresses")
            last = snap
            changes += dw.poll()
            for etype, evidence in changes:
                source = "drive" if etype == "file_public" else "gmail"
                entity = f"file:{evidence['file_id']}" if etype == "file_public" else "gmail:clinic"
                r = requests.post(f"{BRAIN_URL}/events", json=make_event(source, etype, entity, evidence), timeout=10)
                print(etype, "->", r.status_code)
        except Exception as e:
            print("poll error:", e)          # keep going; one bad poll must not stop the watcher
        time.sleep(POLL_SECONDS)

if __name__ == "__main__":
    main()
