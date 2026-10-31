"""Evaluation set A: how well does the Gmail rule scorer separate normal filters from attacker filters?
Run:  python -m eval.run_eval          (prints caught / missed / false alarms at each threshold)
Note: malicious cases are run WITHOUT the 'recent change' bonus, so these numbers are a worst case."""
import json, os
from brain.scoring import score_filter

def main():
    cases = json.load(open(os.path.join(os.path.dirname(__file__), "cases_filters.json")))
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

if __name__ == "__main__":
    main()
