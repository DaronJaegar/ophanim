"""Ransomware detection: the 2-of-3 rule (Ayan, Module C).
Signals: (1) a decoy file is touched, (2) newly written files look random (high entropy),
(3) a burst of renames. Any 2 different signals within WINDOW seconds = ransomware."""
import math, os, time
from collections import Counter, deque

WINDOW = 60
ENTROPY_LIMIT = 7.5          # bits per byte; random/encrypted data is close to 8.0
RENAME_BURST = 20            # renames inside WINDOW
ENTROPY_HITS = 5             # high-entropy writes inside WINDOW
DECOY_NAMES = ["!000_Patient_Records_2026.xlsx", "!000_Accounts_Backup.docx", "zzz_Salary_Register.xlsx"]
SKIP_EXT = {".zip", ".jpg", ".jpeg", ".png", ".mp4", ".gz", ".7z", ".rar", ".pdf"}   # already random-looking

def shannon_entropy(data: bytes) -> float:
    if not data:
        return 0.0
    n = len(data)
    return -sum(c / n * math.log2(c / n) for c in Counter(data).values())

def file_entropy(path, size=4096):
    try:
        with open(path, "rb") as f:
            return shannon_entropy(f.read(size))
    except OSError:
        return 0.0

class Detector:
    def __init__(self, now=time.time):
        self.now = now
        self.signals = {"decoy": deque(), "entropy": deque(), "rename": deque()}
        self.fired = False

    def _trim(self):
        cutoff = self.now() - WINDOW
        for q in self.signals.values():
            while q and q[0] < cutoff:
                q.popleft()

    def active(self):
        self._trim()
        return {
            "decoy": len(self.signals["decoy"]) > 0,
            "entropy": len(self.signals["entropy"]) >= ENTROPY_HITS,
            "rename": len(self.signals["rename"]) >= RENAME_BURST,
        }

    def on_event(self, kind, path, dest=None):
        """kind: 'modified' | 'moved' | 'deleted' | 'created'. Returns True the first time the rule fires."""
        t = self.now()
        names = [os.path.basename(path)] + ([os.path.basename(dest)] if dest else [])
        if any(n in DECOY_NAMES for n in names):
            self.signals["decoy"].append(t)
        if kind == "moved":
            self.signals["rename"].append(t)
        target = dest or path
        if kind in ("modified", "created", "moved") and os.path.splitext(path)[1].lower() not in SKIP_EXT \
                and os.path.isfile(target) and file_entropy(target) > ENTROPY_LIMIT:
            self.signals["entropy"].append(t)
        a = self.active()
        if not self.fired and sum(a.values()) >= 2:
            self.fired = True
            return True
        return False

def plant_decoys(folder):
    for name in DECOY_NAMES:
        p = os.path.join(folder, name)
        if not os.path.exists(p):
            with open(p, "w") as f:
                f.write("Decoy file planted by Chakravyuh. Do not open or edit.\n")
