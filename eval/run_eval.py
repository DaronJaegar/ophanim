"""Evaluation sets.  Run:  python -m eval.run_eval
A: Gmail rule scorer (caught / missed / false alarms at each threshold).
   Note: malicious cases are run WITHOUT the 'recent change' bonus, so these numbers are a worst case.
B: PC file activity through the 2-of-3 ransomware detector (fake ransomware vs zip, backup, renames...).
C: incident pairs through the correlator (related must merge, unrelated must not)."""
import json, os, random, tempfile
from datetime import datetime, timedelta, timezone
from brain.scoring import score_filter
from brain.correlate import Incidents
from agent.detector import Detector, plant_decoys, DECOY_NAMES

HERE = os.path.dirname(__file__)

def load(name):
    with open(os.path.join(HERE, name)) as f:
        return json.load(f)

def run_set_a():
    cases = load("cases_filters.json")
    print("Set A: Gmail filters")
    print(f"{'threshold':>9} | {'caught':>8} | {'missed':>6} | {'false alarms':>12}")
    for th in (3, 4, 5):
        caught = sum(score_filter(f)["score"] >= th for f in cases["malicious"])
        fa = sum(score_filter(f)["score"] >= th for f in cases["benign"])
        print(f"{th:>9} | {caught:>3}/{len(cases['malicious']):<4} | {len(cases['malicious']) - caught:>6} | {fa:>4}/{len(cases['benign'])}")
    print("\nFalse alarms at 3:")
    for f in cases["benign"]:
        s = score_filter(f)
        if s["score"] >= 3:
            print(" ", f["criteria"], s["markers"])

def _write(p, data):
    with open(p, "wb") as f:
        f.write(data)

def play(sc, folder):
    """Replay one scenario into a fresh Detector; return True if the rule fired."""
    d, fired, n, kind = Detector(), False, sc["files"], sc["kind"]
    rnd = random.Random(1)
    text = b"Patient follow-up on Monday. BP normal.\n" * 50
    rand = lambda: bytes(rnd.getrandbits(8) for _ in range(4096))
    if sc.get("decoy"):
        plant_decoys(folder)
    for i in range(n):
        p = os.path.join(folder, f"f{i}.txt")
        if kind == "ransomware":
            _write(p, rand()); fired |= d.on_event("modified", p)
            os.rename(p, p + ".locked"); fired |= d.on_event("moved", p, p + ".locked")
        elif kind == "encrypt_in_place":
            _write(p, rand()); fired |= d.on_event("modified", p)
        elif kind == "zip":
            p = os.path.join(folder, "archive.zip"); _write(p, rand()); fired |= d.on_event("created", p)
        elif kind == "backup":
            _write(p, text); fired |= d.on_event("created", p)
        elif kind in ("bulk_rename", "photo_rename"):
            ext = ".jpg" if kind == "photo_rename" else ".docx"
            p = os.path.join(folder, f"IMG_{i}{ext}"); q = os.path.join(folder, f"Renamed_{i}{ext}")
            _write(p, rand() if kind == "photo_rename" else text)
            os.rename(p, q); fired |= d.on_event("moved", p, q)
        elif kind == "edit_docs":
            _write(p, text); fired |= d.on_event("modified", p)
        elif kind == "archives":
            p = os.path.join(folder, f"a{i}.7z"); _write(p, rand()); fired |= d.on_event("created", p)
        elif kind == "pdfs":
            p = os.path.join(folder, f"d{i}.pdf"); _write(p, rand()); fired |= d.on_event("created", p)
    if sc.get("decoy"):
        fired |= d.on_event("modified", os.path.join(folder, DECOY_NAMES[0]))
    return fired

def run_set_b():
    sets = load("cases_pc.json")["scenarios"]
    print("\nSet B: PC file activity (2-of-3 rule)")
    ok = 0
    for sc in sets:
        with tempfile.TemporaryDirectory() as folder:
            fired = play(sc, folder)
        good = fired == sc["expect_fire"]
        ok += good
        print(f"  {'OK  ' if good else 'FAIL'} fired={fired!s:5} expected={sc['expect_fire']!s:5} {sc['name']}")
    print(f"  correct {ok}/{len(sets)}")

def run_set_c():
    pairs = load("cases_incidents.json")["pairs"]
    print("\nSet C: incident correlation")
    ok, t0 = 0, datetime.now(timezone.utc)
    for c in pairs:
        inc = Incidents()
        inc.add_signal({"type": "x", "entity": c["first"], "evidence": {}}, "high", "t", now=t0)
        _, merged = inc.add_signal({"type": "y", "entity": c["second"], "evidence": {}}, "high", "t",
                                   now=t0 + timedelta(minutes=c["gap_minutes"]))
        good = merged == c["expect_merge"]
        ok += good
        print(f"  {'OK  ' if good else 'FAIL'} merged={merged!s:5} expected={c['expect_merge']!s:5} {c['name']}")
    print(f"  correct {ok}/{len(pairs)}")

def main():
    run_set_a(); run_set_b(); run_set_c()

if __name__ == "__main__":
    main()
