"""SAFE demo 'ransomware' (Ayan, Module C). Only runs in a folder that contains the marker file
.chakravyuh_test_folder. It overwrites COPIES with random bytes and renames them .locked.
Run:  python -m agent.fake_ransomware /path/to/test/folder"""
import os, sys, time

MARKER = ".chakravyuh_test_folder"

def run(folder, delay=0.05):
    if not os.path.exists(os.path.join(folder, MARKER)):
        sys.exit(f"Refusing: {folder} has no {MARKER} marker. Only run this on the test folder.")
    n = 0
    for root, _, files in os.walk(folder):
        for name in files:
            if name == MARKER or name.endswith(".locked"):
                continue
            p = os.path.join(root, name)
            size = max(os.path.getsize(p), 4096)
            with open(p, "wb") as f:
                f.write(os.urandom(size))
            os.rename(p, p + ".locked")
            n += 1
            time.sleep(delay)
    print("locked", n, "files")

if __name__ == "__main__":
    run(sys.argv[1])
