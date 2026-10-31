"""Reset the clinic Gmail between demo runs (Bruce, Module A).
Deletes every filter that was not in the saved baseline. Forwarding addresses are left alone.

  python -m sensors.reset_gmail --save     # once, on a clean mailbox: remember today's filters
  python -m sensors.reset_gmail            # show what would be deleted
  python -m sensors.reset_gmail --yes      # delete them (evidence saved first, like Remove it)
"""
import json, os, sys
from sensors.google_auth import gmail
from sensors.fixes import delete_filter

BASELINE = "gmail_baseline.json"     # git-ignored: holds the clinic's real filters


def current():
    return gmail().users().settings().filters().list(userId="me").execute().get("filter", [])


def main(args):
    filters = current()
    if "--save" in args:
        with open(BASELINE, "w") as f:
            json.dump([x["id"] for x in filters], f)
        print(f"Baseline saved: {len(filters)} filter(s) in {BASELINE}")
        return
    if not os.path.exists(BASELINE):
        sys.exit(f"No {BASELINE}: run with --save on a clean mailbox first.")
    keep = set(json.load(open(BASELINE)))
    extra = [f for f in filters if f["id"] not in keep]
    for f in extra:
        print("  extra filter:", f.get("criteria", {}), "->", f.get("action", {}))
    if not extra:
        print("Gmail is clean: only baseline filters.")
    elif "--yes" not in args:
        print(f"{len(extra)} filter(s) would be deleted. Run again with --yes to delete.")
    else:
        log = []
        ok = all(delete_filter(f, log) for f in extra)
        print(f"Deleted {len(extra)} filter(s); verified gone: {ok}")


if __name__ == "__main__":
    main(sys.argv[1:])
