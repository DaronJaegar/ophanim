"""Drive sharing watcher (Bruce, Module A): finds files that became 'anyone with the link'."""
SENSITIVE_WORDS = ["patient", "record", "aadhaar", "salary", "invoice", "bank", "medical", "report"]

class DriveWatcher:
    def __init__(self, svc):
        self.svc = svc
        self.token = svc.changes().getStartPageToken().execute()["startPageToken"]
        self.seen_public = set()

    def _parent_public(self, fid):
        """True if a folder holding this file is shared with anyone (sharing a folder of 8 PDFs = 1 alert, not 9)."""
        try:
            parents = self.svc.files().get(fileId=fid, fields="parents").execute().get("parents", [])
            return any(p["type"] == "anyone" for parent in parents for p in
                       self.svc.permissions().list(fileId=parent, fields="permissions(type)").execute().get("permissions", []))
        except Exception:                   # can't tell -> alert anyway (safer than missing it)
            return False

    def poll(self):
        out, token = [], self.token
        while token:
            resp = self.svc.changes().list(pageToken=token, spaces="drive",
                                           fields="nextPageToken,newStartPageToken,changes(fileId,removed,file(name))").execute()
            for ch in resp.get("changes", []):
                fid = ch["fileId"]
                if ch.get("removed"):             # deleted / lost access: nothing to check
                    self.seen_public.discard(fid)
                    continue
                name = ch.get("file", {}).get("name", "")
                try:
                    perms = self.svc.permissions().list(fileId=fid, fields="permissions(id,type,role)").execute()
                except Exception as e:             # one bad file must not stall the whole feed
                    print("drive: skipped", fid, e)
                    continue
                public = [p for p in perms.get("permissions", []) if p["type"] == "anyone"]
                if not public:
                    self.seen_public.discard(fid)  # made private again -> re-sharing alerts again
                elif self._parent_public(fid):      # public only through its folder: the folder's alert covers it
                    continue
                elif fid not in self.seen_public:
                    self.seen_public.add(fid)
                    out.append(("file_public", {"file_id": fid, "name": name,
                                                "permission_id": public[0]["id"],
                                                "sensitive": any(w in name.lower() for w in SENSITIVE_WORDS)}))
            token = resp.get("nextPageToken")
            if resp.get("newStartPageToken"):
                self.token = resp["newStartPageToken"]
        return out
