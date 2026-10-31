"""One-tap fixes (Bruce, Module A). Evidence is saved BEFORE anything is removed."""
from sensors.google_auth import gmail, drive, DRIVE_WRITE_SCOPES

def delete_filter(f, audit):
    svc = gmail()
    audit.append({"kind": "evidence", "what": "gmail_filter", "filter": f})     # 1. preserve
    svc.users().settings().filters().delete(userId="me", id=f["id"]).execute()  # 2. remove
    remaining = svc.users().settings().filters().list(userId="me").execute().get("filter", [])
    gone = all(x["id"] != f["id"] for x in remaining)                           # 3. re-read to verify
    audit.append({"kind": "fix", "what": "delete_filter", "id": f["id"], "verified": gone})
    return gone

def make_private(file_id, audit):
    svc = drive(DRIVE_WRITE_SCOPES, "token_drive_write.json")   # asks for write access the first time only
    perms = svc.permissions().list(fileId=file_id, fields="permissions(id,type,role)").execute()
    audit.append({"kind": "evidence", "what": "drive_permissions", "file_id": file_id, "perms": perms})
    for p in perms.get("permissions", []):
        if p["type"] == "anyone":
            svc.permissions().delete(fileId=file_id, permissionId=p["id"]).execute()
    after = svc.permissions().list(fileId=file_id, fields="permissions(type)").execute()
    ok = all(p["type"] != "anyone" for p in after.get("permissions", []))
    audit.append({"kind": "fix", "what": "make_private", "file_id": file_id, "verified": ok})
    return ok
