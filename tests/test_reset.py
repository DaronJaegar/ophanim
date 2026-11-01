"""One-command reset, with fakes only: never the real Gmail, Drive, brain or processes.  python -m pytest tests -q"""
from types import SimpleNamespace
from scripts import reset_demo as R

RANSOM = {"id": 4, "status": "open", "signals": [{"type": "filter_added"}, {"type": "ransomware_suspected"}]}
EMAIL = {"id": 5, "status": "open", "signals": [{"type": "filter_added"}]}
CLOSED = {"id": 6, "status": "closed", "signals": [{"type": "ransomware_suspected"}]}


def test_pc_actions_release_then_restore_only_for_open_ransomware():
    assert R.pc_actions([RANSOM, EMAIL, CLOSED]) == [(4, "release_pc"), (4, "restore_files")]


class FakeHttp:
    def __init__(self, incs, restored=True):
        self.incs, self.posted, self.restored = incs, [], restored

    def get(self, url, timeout=None):
        body = self.incs if url.endswith("/incidents") else {"rows": [{"body": {"type": "files_restored"}}] if self.restored else []}
        return SimpleNamespace(json=lambda: body)

    def post(self, url, json=None, headers=None, timeout=None):
        self.posted.append((json, headers))
        return SimpleNamespace(status_code=200, content=b"{}", json=lambda: {"queued": True})


def test_pc_step_posts_owner_actions_and_dry_run_posts_nothing(monkeypatch):
    monkeypatch.setattr(R, "OWNER_CHAT_ID", "111")
    monkeypatch.setattr(R, "brain_headers", lambda: {"X-Brain-Token": "t"})
    http = FakeHttp([RANSOM])
    R.step_pc(True, http)
    assert http.posted == []
    R.step_pc(False, http, wait=3)
    assert [p[0]["action"] for p in http.posted] == ["release_pc", "restore_files"]
    assert all(p[0]["by"] == "111" and p[1] == {"X-Brain-Token": "t"} for p in http.posted)


class FakeDrive:
    def files(self): return self
    def list(self, q, fields):
        assert "anyoneWithLink" in q
        return SimpleNamespace(execute=lambda: {"files": [{"id": "F", "name": "Patient records"}]})


def test_drive_step_makes_public_files_private_only_when_not_dry():
    fixed = []
    R.step_drive(True, svc=FakeDrive(), fix=lambda fid, audit: fixed.append(fid))
    assert fixed == []
    R.step_drive(False, svc=FakeDrive(), fix=lambda fid, audit: fixed.append(fid) or True)
    assert fixed == ["F"]


def test_only_our_processes_are_stopped():
    P = lambda pid, cmd: SimpleNamespace(info={"pid": pid, "cmdline": cmd.split()})
    procs = [P(1, "python -m uvicorn brain.app:app --port 8000"), P(2, "python -m sensors.run"),
             P(3, "python -m sahayak.bot"), P(4, "python -m scripts.reset_demo"), P(5, "chrome.exe"),
             P(6, "python -m agent.agent")]
    assert R.targets(procs, me=99) == [(1, "brain"), (2, "sensors"), (3, "bot")]


def test_db_is_moved_not_deleted(tmp_path, monkeypatch):
    from sahayak import signing
    monkeypatch.setattr(signing, "USED_TAPS_FILE", "")
    db, runs = tmp_path / "chakravyuh.db", tmp_path / "runs"
    db.write_text("audit")
    R.step_db(True, str(db), str(runs))
    assert db.exists() and not runs.exists()                     # dry run: untouched
    R.step_db(False, str(db), str(runs))
    assert not db.exists() and [p.read_text() for p in runs.iterdir()] == ["audit"]
