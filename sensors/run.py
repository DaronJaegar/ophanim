"""Run the watchers and send every change to the brain (Bruce, Module A).
Run:  python -m sensors.run
"""
import time, requests
from common.config import BRAIN_URL, POLL_SECONDS, brain_headers
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
            try:
                changes += dw.poll()     # a Drive problem must never block Gmail alerts
            except Exception as e:
                print("drive poll error:", e)
            delivered = True
            for etype, evidence in changes:
                source = "drive" if etype == "file_public" else "gmail"
                entity = f"file:{evidence['file_id']}" if etype == "file_public" else "gmail:clinic"
                try:
                    r = requests.post(f"{BRAIN_URL}/events", json=make_event(source, etype, entity, evidence),
                                      headers=brain_headers(), timeout=10)
                    print(etype, "->", r.status_code)
                    delivered = delivered and r.ok
                except requests.RequestException as e:
                    print(etype, "-> brain unreachable:", e)
                    delivered = False
            if delivered or last is None:
                last = snap              # only move on once the brain has every Gmail change
            else:
                print("brain did not accept every event; Gmail changes will be resent next poll")
        except Exception as e:
            print("poll error:", e)          # keep going; one bad poll must not stop the watcher
        time.sleep(POLL_SECONDS)

if __name__ == "__main__":
    main()
