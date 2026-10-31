"""Incidents, correlation and runbook ordering (Aaron, Module B)."""
import itertools
from datetime import datetime, timedelta, timezone
from common.config import PEOPLE

SEVERITY = ["low", "medium", "high", "critical"]
_ids = itertools.count(1)

def expand_entities(entity):
    """Add the person behind an account or device, so 'gmail:clinic' and 'device:frontdesk-pc' meet at 'person:priya'."""
    out = {entity}
    for person, owns in PEOPLE.items():
        if any(entity.endswith(x) for x in owns["accounts"] + owns["devices"]):
            out.add(f"person:{person}")
    return out

def runbook(kinds):
    """The response order. If a PC is involved, contain it first and change passwords from a clean device."""
    pc = "device" in kinds
    email = "account" in kinds
    steps = []
    if pc:
        steps += ["contain_pc"]
    if email:
        steps += ["save_evidence", "confirm_with_owner", "remove_attacker_rules"]
    if email or pc:
        steps += ["change_password_from_clean_device" if pc else "change_password",
                  "sign_out_other_devices", "check_payments", "report"]
    return steps

class Incidents:
    def __init__(self):
        self.items = {}

    def _kind(self, entity):
        return "device" if entity.startswith("device:") else (
            "account" if entity.startswith(("gmail:", "file:", "drive:", "honeytoken:")) else "other")

    def add_signal(self, signal, severity, title, policy="tap", now=None, merge=True):
        """signal = {'type','entity','evidence'}. Returns (incident, merged: bool).
        merge=False: an information-only alert (e.g. old backup) gets its own incident and is not expanded
        to the person, so a later attack on the same PC never merges into it."""
        now = now or datetime.now(timezone.utc)
        ents = expand_entities(signal["entity"]) if merge else {signal["entity"]}
        for inc in (self.items.values() if merge else []):
            if inc["status"] == "open" and inc["entities"] & ents and \
               now - inc["updated"] <= timedelta(hours=24):
                inc["signals"].append(signal)
                inc["entities"] |= ents
                inc["kinds"].add(self._kind(signal["entity"]))
                if len(inc["kinds"]) > 1:            # email + PC in one story: raise one level
                    inc["severity"] = SEVERITY[min(3, max(SEVERITY.index(inc["severity"]),
                                                          SEVERITY.index(severity)) + 1)]
                    inc["title"] = "Priya's email and her computer are both under attack"
                else:
                    inc["severity"] = max(inc["severity"], severity, key=SEVERITY.index)
                inc["policy"] = "auto" if "auto" in (inc["policy"], policy) else "tap"
                inc["runbook"] = runbook(inc["kinds"])
                inc["updated"] = now
                return inc, True
        iid = next(_ids)
        kinds = {self._kind(signal["entity"])}
        inc = {"id": iid, "title": title, "severity": severity, "signals": [signal],
               "entities": ents, "kinds": kinds, "policy": policy, "status": "open",
               "runbook": runbook(kinds), "done": [], "created": now, "updated": now}
        self.items[iid] = inc
        return inc, False

    def public(self, inc):
        return {k: (sorted(v) if isinstance(v, set) else (v.isoformat() if isinstance(v, datetime) else v))
                for k, v in inc.items()}
