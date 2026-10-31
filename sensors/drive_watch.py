"""Drive sharing watcher (Bruce, Module A): finds files that became 'anyone with the link'."""
SENSITIVE_WORDS = ["patient", "record", "aadhaar", "salary", "invoice", "bank", "medical", "report"]

class DriveWatcher:
    def __init__(self, svc):
        self.svc = svc
        self.token = svc.changes().getStartPageToken().execute()["startPageToken"]
        self.seen_public = set()

    def poll(self):
        out, token = [], self.token
        while token:
            resp = self.svc.changes().list(pageToken=token, spaces="drive",
                                           fields="nextPageToken,newStartPageToken,changes(fileId,file(name))").execute()
            for ch in resp.get("changes", []):
                fid = ch["fileId"]
                name = ch.get("file", {}).get("name", "")
                perms = self.svc.permissions().list(fileId=fid, fields="permissions(id,type,role)").execute()
                public = [p for p in perms.get("permissions", []) if p["type"] == "anyone"]
                if public and fid not in self.seen_public:
                    self.seen_public.add(fid)
                    out.append(("file_public", {"file_id": fid, "name": name,
                                                "permission_id": public[0]["id"],
                                                "sensitive": any(w in name.lower() for w in SENSITIVE_WORDS)}))
            token = resp.get("nextPageToken")
            if resp.get("newStartPageToken"):
                self.token = resp["newStartPageToken"]
        return out
