"""Gmail settings watcher (Bruce, Module A).
Gmail has no push notification for settings, so we poll and compare with the last snapshot.
"""

def snapshot(svc):
    """Everything an attacker might change, keyed so we can diff it."""
    s = svc.users().settings()
    filters = s.filters().list(userId="me").execute().get("filter", [])
    fwd = s.forwardingAddresses().list(userId="me").execute().get("forwardingAddresses", [])
    auto = s.getAutoForwarding(userId="me").execute()
    send_as = s.sendAs().list(userId="me").execute().get("sendAs", [])
    return {
        "filters": {f["id"]: f for f in filters},
        "forwarding": {a["forwardingEmail"]: a.get("verificationStatus", "") for a in fwd},
        "autoforward": auto.get("enabled", False),
        "autoforward_to": auto.get("emailAddress", ""),
        "send_as": {a["sendAsEmail"]: a for a in send_as},
    }

def diff(old, new):
    """Return a list of (event_type, evidence) for anything new since the last snapshot."""
    if old is None:                 # first run = the baseline; owner confirms these once
        return []
    out = []
    for fid, f in new["filters"].items():
        if fid not in old["filters"]:
            out.append(("filter_added", {"filter": f}))
    for email, status in new["forwarding"].items():
        if email not in old["forwarding"]:
            out.append(("forwarding_added", {"address": email, "status": status}))
    if new["autoforward"] and not old["autoforward"]:
        out.append(("autoforward_on", {"to": new["autoforward_to"]}))
    for email in new["send_as"]:
        if email not in old["send_as"]:
            out.append(("sendas_added", {"address": email}))
    return out
