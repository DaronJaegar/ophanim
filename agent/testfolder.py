"""Make and restore the demo test folder (Ayan, Module C).
  python -m agent.testfolder make    /path/ClinicFiles   (creates 60 sample files + a backup)
  python -m agent.testfolder restore /path/ClinicFiles   (puts the originals back after the demo)"""
import os, shutil, sys
from agent.fake_ransomware import MARKER

def make(folder, n=60):
    os.makedirs(folder, exist_ok=True)
    open(os.path.join(folder, MARKER), "w").close()
    for i in range(n):
        with open(os.path.join(folder, f"patient_note_{i:03}.txt"), "w") as f:
            f.write(f"Patient {i}: follow-up visit on Monday. Blood pressure normal.\n" * 20)
    shutil.copytree(folder, folder + "_backup", dirs_exist_ok=True)
    print("made", n, "files and", folder + "_backup")

def restore(folder):
    shutil.rmtree(folder, ignore_errors=True)
    shutil.copytree(folder + "_backup", folder)
    print("restored", folder)

if __name__ == "__main__":
    {"make": make, "restore": restore}[sys.argv[1]](sys.argv[2])
