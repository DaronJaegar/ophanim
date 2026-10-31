"""Drive sharing with a fake Drive: a shared folder of PDFs.  python -m pytest tests -q"""
import httplib2
from googleapiclient.errors import HttpError
from sensors.drive_watch import DriveWatcher
from sensors.fixes import make_private


class Call:
    def __init__(self, fn):
        self.fn = fn

    def execute(self):
        return self.fn()


class FakeDrive:
    """folder 'F' holds 'pdf1' and 'pdf2'. Sharing F makes the PDFs public by inheritance."""
    def __init__(self):
        self.own = {"F": set(), "pdf1": set(), "pdf2": set()}     # files with their own 'anyone' link
        self.parents = {"pdf1": ["F"], "pdf2": ["F"], "F": []}
        self.changed = []

    def public(self, fid):
        return bool(self.own[fid]) or any(self.public(p) for p in self.parents[fid])

    # files() / permissions() / changes() each return self; method names are distinct
    def files(self): return self
    def permissions(self): return self
    def changes(self): return self

    def get(self, fileId, fields):
        return Call(lambda: {"parents": self.parents[fileId]})

    def list(self, fileId=None, fields=None, pageToken=None, spaces=None):
        if pageToken is not None:                               # changes().list
            out, self.changed = self.changed, []
            return Call(lambda: {"newStartPageToken": "t", "changes": [{"fileId": f, "file": {"name": f}} for f in out]})
        perms = [{"id": "owner", "type": "user", "role": "owner"}]
        if self.public(fileId):
            perms.append({"id": "anyoneWithLink", "type": "anyone", "role": "reader"})
        return Call(lambda: {"permissions": perms})

    def delete(self, fileId, permissionId):
        def run():
            if not self.own[fileId]:                            # inherited: Google refuses
                raise HttpError(httplib2.Response({"status": 403}), b"inherited")
            self.own[fileId].clear()
        return Call(run)

    def getStartPageToken(self):
        return Call(lambda: {"startPageToken": "t"})

    def share_folder(self):
        self.own["F"].add("anyone")
        self.changed = ["F", "pdf1", "pdf2"]


def test_sharing_a_folder_gives_one_alert_not_one_per_file():
    d = FakeDrive()
    w = DriveWatcher(d)
    d.share_folder()
    assert [e[1]["file_id"] for e in w.poll()] == ["F"]


def test_make_private_on_a_pdf_makes_its_folder_private():
    d = FakeDrive()
    d.share_folder()
    audit = []
    assert make_private("pdf1", audit, svc=d) is True
    assert not d.public("F") and not d.public("pdf2")
    assert audit[-1] == {"kind": "fix", "what": "make_private", "file_id": "pdf1", "verified": True}


def test_resharing_after_make_private_alerts_again():
    d = FakeDrive()
    w = DriveWatcher(d)
    d.share_folder(); w.poll()
    make_private("F", [], svc=d); d.changed = ["F"]; w.poll()
    d.share_folder()
    assert [e[1]["file_id"] for e in w.poll()] == ["F"]
