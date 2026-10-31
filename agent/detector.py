"""Ransomware detection: the 2-of-3 rule (Ayan, Module C).
Signals: (1) a decoy file is touched, (2) newly written files look random (high entropy),
(3) a burst of renames. Any 2 different signals within WINDOW seconds = ransomware.
Upgrade: files renamed to an unusual extension (.txt -> .locked) strengthen the rename signal:
EXT_BURST of them count as a rename burst, because normal bulk renames keep familiar extensions."""
import math, os, re, threading, time
from collections import Counter, deque

WINDOW = 60
ENTROPY_LIMIT = 7.5          # bits per byte; random/encrypted data is close to 8.0
RENAME_BURST = 20            # renames inside WINDOW
EXT_BURST = 5                # renames to an unusual extension inside WINDOW (also a rename burst)
ENTROPY_HITS = 5             # high-entropy writes inside WINDOW
DECOY_NAMES = ["!000_Patient_Records_2026.xlsx", "!000_Accounts_Backup.docx", "zzz_Salary_Register.xlsx"]
SKIP_EXT = {".zip", ".jpg", ".jpeg", ".png", ".mp4", ".gz", ".7z", ".rar", ".pdf"}   # already random-looking
KNOWN_EXT = {"", ".txt", ".doc", ".docx", ".xls", ".xlsx", ".csv", ".ppt", ".pptx", ".pdf", ".odt", ".ods",
             ".rtf", ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tif", ".tiff", ".heic", ".webp", ".mp3", ".wav",
             ".mp4", ".mov", ".avi", ".zip", ".7z", ".rar", ".gz", ".tar", ".xml", ".json", ".html", ".htm",
             ".bak", ".tmp", ".log", ".md"}   # renames TO these are everyday (Office saves, downloads, photos)

# Optional 4th sign (RANSOM_NOTES=1): ransomware drops a note telling you how to pay. Normal work never
# creates files with these names. Off by default, so the 2-of-3 rule and eval set B are unchanged.
NOTE_RE = re.compile(r"(readme.{0,3}(decrypt|restore|recover)|how.{0,3}to.{0,3}(decrypt|restore|recover|back)|"
                     r"(decrypt|restore|recover).{0,3}(files|instructions|my.?files)|^_readme\.txt$|\.hta$)", re.I)

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

def unusual_extension_change(path, dest):
    old, new = os.path.splitext(path)[1].lower(), os.path.splitext(dest)[1].lower()
    return old != new and new not in KNOWN_EXT

class Detector:
    def __init__(self, now=time.time, notes=False):
        self.now = now
        self.notes = notes                 # RANSOM_NOTES: count ransom-note file names as a 4th sign
        self.lock = threading.RLock()      # the watcher thread and the signal meter both read the queues
        self.reset()

    def reset(self):
        """Forget every signal (after a release or a restore), so the rule can fire again."""
        with self.lock:
            self.signals = {"decoy": deque(), "entropy": deque(), "rename": deque(), "extension": deque(),
                            "note": deque()}
            self.fired = False

    def _trim(self):
        cutoff = self.now() - WINDOW
        for q in self.signals.values():
            while q and q[0] < cutoff:
                q.popleft()

    def counts(self):
        with self.lock:
            self._trim()
            return {k: len(q) for k, q in self.signals.items()}

    def active(self):
        c = self.counts()
        out = {
            "decoy": c["decoy"] > 0,
            "entropy": c["entropy"] >= ENTROPY_HITS,
            "rename": c["rename"] >= RENAME_BURST or c["extension"] >= EXT_BURST,
        }
        if self.notes:
            out["note"] = c["note"] > 0
        return out

    def on_event(self, kind, path, dest=None):
        """kind: 'modified' | 'moved' | 'deleted' | 'created'. Returns True the first time the rule fires."""
        with self.lock:
            t = self.now()
            names = [os.path.basename(path)] + ([os.path.basename(dest)] if dest else [])
            if any(n in DECOY_NAMES for n in names):
                self.signals["decoy"].append(t)
            if self.notes and kind in ("created", "moved") and NOTE_RE.search(os.path.basename(dest or path)):
                self.signals["note"].append(t)
            if kind == "moved":
                self.signals["rename"].append(t)
                if dest and unusual_extension_change(path, dest):
                    self.signals["extension"].append(t)
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
