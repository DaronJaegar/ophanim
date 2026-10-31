"""Ayan's detector tests:  python -m pytest tests -q"""
import os
from agent.detector import Detector, plant_decoys, DECOY_NAMES

def write(p, data):
    with open(p, "wb") as f:
        f.write(data)

def test_fake_ransomware_fires(tmp_path):
    plant_decoys(tmp_path)
    d, fired = Detector(), False
    for i in range(10):
        p = tmp_path / f"note_{i}.txt"
        write(p, os.urandom(4096))                          # encrypted-looking content
        fired |= d.on_event("modified", str(p))
        os.rename(p, str(p) + ".locked")
        fired |= d.on_event("moved", str(p), str(p) + ".locked")
    fired |= d.on_event("modified", str(tmp_path / DECOY_NAMES[0]))
    assert fired

def test_normal_edits_do_not_fire(tmp_path):
    d = Detector()
    for i in range(30):
        p = tmp_path / f"note_{i}.txt"
        write(p, b"Patient follow-up on Monday. BP normal.\n" * 50)
        assert not d.on_event("modified", str(p))

def test_renaming_photos_does_not_fire(tmp_path):
    d = Detector()                                          # rename burst alone is only 1 of 3 signals
    for i in range(40):
        p = tmp_path / f"IMG_{i}.jpg"
        write(p, os.urandom(4096))
        os.rename(p, tmp_path / f"Holiday_{i}.jpg")
        assert not d.on_event("moved", str(p), str(tmp_path / f"Holiday_{i}.jpg"))

def test_unusual_extension_strengthens_renames(tmp_path):
    d = Detector()                                          # 6 files -> .locked: too few for a rename burst,
    for i in range(6):                                      # but enough odd extensions to count as one
        p = tmp_path / f"note_{i}.txt"
        write(p, b"Patient follow-up on Monday.\n" * 20)
        os.rename(p, str(p) + ".locked")
        d.on_event("moved", str(p), str(p) + ".locked")
    assert d.active()["rename"] and not d.fired
    assert d.on_event("modified", str(tmp_path / DECOY_NAMES[0]))   # + decoy = 2 of 3

def test_familiar_extension_changes_do_not_fire(tmp_path):
    d = Detector()                                          # 40 photos .jpeg -> .jpg + a decoy touch: still quiet
    for i in range(40):
        p = tmp_path / f"IMG_{i}.jpeg"
        write(p, b"x" * 100)
        os.rename(p, tmp_path / f"IMG_{i}.jpg")
        assert not d.on_event("moved", str(p), str(tmp_path / f"IMG_{i}.jpg"))
    assert d.counts()["extension"] == 0

def test_reset_rearms_the_rule(tmp_path):
    d = Detector()
    d.on_event("modified", str(tmp_path / DECOY_NAMES[0]))
    d.fired = True
    d.reset()
    assert not d.fired and d.counts()["decoy"] == 0

def test_restore_refuses_unmarked_backup_and_restores_marked(tmp_path, monkeypatch):
    agent = __import__("agent.agent", fromlist=["x"])
    from agent.fake_ransomware import MARKER
    watch, backup = tmp_path / "Clinic", tmp_path / "Clinic_backup"
    watch.mkdir(); backup.mkdir()
    write(backup / "note.txt", b"original")
    write(watch / "note.txt.locked", os.urandom(64))
    monkeypatch.setattr(agent, "WATCH_DIR", str(watch))
    monkeypatch.setattr(agent, "BACKUP_DIR", str(backup))
    monkeypatch.setattr(agent.time, "sleep", lambda s: None)
    assert agent.restore_files(Detector()) == 0 and (watch / "note.txt.locked").exists()   # no marker: refuse
    write(backup / MARKER, b"")
    assert agent.restore_files(Detector()) > 0
    assert (watch / "note.txt").read_bytes() == b"original" and not (watch / "note.txt.locked").exists()
    assert all((watch / n).exists() for n in DECOY_NAMES)


def test_ransom_note_is_a_4th_sign_only_when_switched_on(tmp_path):
    from agent.detector import NOTE_RE
    names = ["README_DECRYPT.txt", "HOW_TO_RECOVER_FILES.html", "_readme.txt", "restore-my-files.txt", "info.hta"]
    normal = ["README.md", "how_to_book_appointments.docx", "recovery_plan_2026.docx", "restore_points.xlsx",
              "readme.txt", "Decrypted_report_final.pdf"]
    assert all(NOTE_RE.search(n) for n in names) and not any(NOTE_RE.search(n) for n in normal)
    plant_decoys(tmp_path)
    off, on = Detector(), Detector(notes=True)
    for d in (off, on):
        d.on_event("created", str(tmp_path / "README_DECRYPT.txt"))
        d.on_event("modified", str(tmp_path / DECOY_NAMES[0]))           # note + decoy = 2 signs
    assert "note" not in off.active() and not off.fired                   # off: behaviour unchanged
    assert on.active()["note"] and on.fired


def test_pc_health_returns_none_off_windows(monkeypatch):
    from agent import upgrades
    monkeypatch.setattr(upgrades.os, "name", "posix")
    assert upgrades.pc_health() is None
