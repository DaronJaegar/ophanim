"""Which process the agent freezes (agent/upgrades.top_writer_now), with fake processes: no real I/O, no sleeping."""
import os
import agent.upgrades as U

class FakeIO:
    def __init__(self, w): self.write_bytes = w

class FakeP:
    def __init__(self, pid, name, rate, cmd=(), started=0.0):
        self.pid, self._name, self.rate, self.cmd, self.started, self.calls = pid, name, rate, list(cmd), started, 0
    def name(self): return self._name
    def io_counters(self):
        self.calls += 1
        return FakeIO(self.rate * self.calls)          # wrote `rate` bytes between the two samples
    def cmdline(self): return self.cmd
    def open_files(self): return []
    def create_time(self): return self.started

WATCH = os.path.abspath("ClinicFiles")

def run(monkeypatch, procs, **kw):
    monkeypatch.setattr(U.psutil, "process_iter", lambda attrs=None: procs)
    monkeypatch.setattr(U.time, "sleep", lambda s: None)
    monkeypatch.setattr(U, "_agent_family", lambda: {1})
    return U.top_writer_now(**kw)

def ide(): return FakeP(10, "Code.exe", 5_000_000, started=100.0)            # busy, but running before the agent
def ransom(cmd=(), started=500.0): return FakeP(20, "python.exe", 80_000, cmd, started)

def test_busy_ide_is_not_frozen_ransomware_in_folder_is(monkeypatch):
    p = run(monkeypatch, [ide(), ransom(["python", "-m", "agent.fake_ransomware", WATCH])], folder=WATCH, since=400.0)
    assert p.pid == 20

def test_new_writer_picked_when_no_folder_hint(monkeypatch):
    p = run(monkeypatch, [ide(), ransom()], folder=WATCH, since=400.0)
    assert p.pid == 20

def test_no_suspect_freezes_nothing(monkeypatch):
    assert run(monkeypatch, [ide()], folder=WATCH, since=400.0) is None

def test_agent_itself_and_system_never_frozen(monkeypatch):
    procs = [FakeP(1, "python.exe", 9_000_000, [WATCH], 500.0), FakeP(4, "MsMpEng.exe", 9_000_000, [WATCH], 500.0)]
    assert run(monkeypatch, procs, folder=WATCH, since=400.0) is None

def test_python_is_no_longer_safe():
    assert "python.exe" not in U.SAFE
