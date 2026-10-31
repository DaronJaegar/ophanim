"""Venue benign baseline: how many alerts per hour does normal use cause? (Aaron, Module B)

Run the brain + sensors.run on the clinic account while people use it normally (no attack),
then:  python -m eval.venue_baseline [chakravyuh.db] [--since 2026-11-07T10:00]
Reads the audit log only (never writes), so it is safe while the brain is running.
"""
import json, sqlite3, sys
from collections import Counter
from datetime import datetime

def load(path, since=None):
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    rows = [json.loads(b) for (b,) in db.execute("SELECT body FROM audit ORDER BY id")]
    events = [r for r in rows if r.get("kind") == "event" and r.get("ts")]
    if since:
        events = [e for e in events if e["ts"] >= since]
    return events

def summary(events):
    if not events:
        return None
    ts = [datetime.fromisoformat(e["ts"]) for e in events]
    hours = max((max(ts) - min(ts)).total_seconds() / 3600, 1 / 60)     # at least one minute
    from brain.scoring import score_filter                               # re-score: the audit row has the raw filter
    from common.config import CLINIC_DOMAIN
    levels = Counter()
    for e in events:
        if e["type"] == "filter_added":
            levels[score_filter(e["evidence"].get("filter", {}), CLINIC_DOMAIN)["level"]] += 1
        elif e["type"] not in ("heartbeat_missing",):
            levels["alert"] += 1                                         # every other sensor event opens an incident
    return {"from": min(ts).isoformat(timespec="minutes"), "to": max(ts).isoformat(timespec="minutes"),
            "hours": round(hours, 2), "events": len(events), "by_type": dict(Counter(e["type"] for e in events)),
            "alerts": levels["alert"], "asks": levels["ask"], "digest": levels["digest"],
            "alerts_per_hour": round(levels["alert"] / hours, 2), "asks_per_hour": round(levels["ask"] / hours, 2)}

def main(argv):
    path = next((a for a in argv if not a.startswith("--") and not a[:1].isdigit()), "chakravyuh.db")
    since = argv[argv.index("--since") + 1] if "--since" in argv else None
    s = summary(load(path, since))
    if not s:
        print("No events in", path, "(since " + since + ")" if since else "")
        return
    print(f"Window {s['from']} -> {s['to']} UTC ({s['hours']} h), {s['events']} events: {s['by_type']}")
    print(f"Alerts: {s['alerts']} ({s['alerts_per_hour']}/h)   Asks: {s['asks']} ({s['asks_per_hour']}/h)   Digest only: {s['digest']}")
    print("For the slide: run during normal use only; any attack or test event in the window inflates the numbers.")

if __name__ == "__main__":
    main(sys.argv[1:])
