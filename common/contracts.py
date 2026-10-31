"""The three shared contracts. Change these only after telling Aaron."""
from datetime import datetime, timezone

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def make_event(source, type_, entity, evidence=None):
    """POST /events body.
    source: gmail | drive | agent | honeytoken | sahayak | brain
    type_:  filter_added | forwarding_added | autoforward_on | sendas_added | file_public |
            ransomware_suspected | heartbeat_missing | honeytoken_hit | bank_change_request
    entity: what it is about, e.g. "gmail:clinic", "device:frontdesk-pc", "file:<id>"
    """
    return {"source": source, "type": type_, "entity": entity,
            "evidence": evidence or {}, "ts": now_iso()}
