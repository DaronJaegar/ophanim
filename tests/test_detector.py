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
