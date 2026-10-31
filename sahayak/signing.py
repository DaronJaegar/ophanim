"""Signed, expiring, one-time buttons (Aradhya, Module D).
Telegram allows only 64 bytes of callback_data, so the format is short:  <incident>|<code>|<expiry>|<sig>"""
import hashlib, hmac, time
from common.config import HMAC_SECRET

_used = set()          # one-time: a replayed tap is rejected

def _sig(payload):
    return hmac.new(HMAC_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()[:12]

def make(incident_id, code, ttl=900):
    exp = int(time.time()) + ttl
    payload = f"{incident_id}|{code}|{exp}"
    data = f"{payload}|{_sig(payload)}"
    assert len(data.encode()) <= 64, "callback_data too long"
    return data

class BadTap(Exception):
    pass

def verify(data, now=None):
    try:
        iid, code, exp, sig = data.split("|")
    except ValueError:
        raise BadTap("malformed")
    payload = f"{iid}|{code}|{exp}"
    if not hmac.compare_digest(sig, _sig(payload)):
        raise BadTap("signature does not match")
    if (now or time.time()) > int(exp):
        raise BadTap("expired")
    if data in _used:
        raise BadTap("already used")
    _used.add(data)
    return int(iid), code
