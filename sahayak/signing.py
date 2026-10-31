"""Signed, expiring, one-time buttons (Aradhya, Module D).
Telegram allows only 64 bytes of callback_data, so the format is short:
    <incident>|<code>|<expiry>|<nonce>|<sig>     sig = HMAC-SHA256(secret, everything before it)[:12]
- nonce: the owner's and staff's copies of the same button must differ, or one tap "uses up" the other.
- Action buttons work once; read-only buttons (why / how / st) can be tapped again.
- Used taps are also written to a small file, so restarting the bot doesn't re-open old buttons."""
import hashlib, hmac, os, secrets, time
from common.config import HMAC_SECRET, USED_TAPS_FILE

TTL = 900                              # 15 minutes
REUSABLE = {"why", "how", "st"}        # only explain; safe to tap twice
_used = None


class BadTap(Exception):
    pass


def _sig(payload):
    return hmac.new(HMAC_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()[:12]


def _load_used():
    global _used
    if _used is None:
        _used = set()
        if USED_TAPS_FILE and os.path.exists(USED_TAPS_FILE):
            with open(USED_TAPS_FILE, encoding="utf-8") as f:
                _used = {line.strip() for line in f if line.strip()}
    return _used


def _mark_used(data):
    _load_used().add(data)
    if USED_TAPS_FILE:
        try:
            with open(USED_TAPS_FILE, "a", encoding="utf-8") as f:
                f.write(data + "\n")
        except OSError:
            pass                       # memory still protects us until a restart


def reset_used():
    """Tests and the demo reset."""
    global _used
    _used = set()
    if USED_TAPS_FILE and os.path.exists(USED_TAPS_FILE):
        os.remove(USED_TAPS_FILE)


def make(incident_id, code, ttl=TTL, now=None):
    exp = int(now or time.time()) + ttl
    payload = f"{incident_id}|{code}|{exp}|{secrets.token_hex(2)}"
    data = f"{payload}|{_sig(payload)}"
    assert len(data.encode()) <= 64, "callback_data too long"
    return data


def verify(data, now=None):
    try:
        iid, code, exp, nonce, sig = data.split("|")
        int(iid), int(exp)
    except ValueError:
        raise BadTap("malformed")
    payload = f"{iid}|{code}|{exp}|{nonce}"
    if not hmac.compare_digest(sig, _sig(payload)):
        raise BadTap("signature does not match")
    if (now or time.time()) > int(exp):
        raise BadTap("expired")
    if code not in REUSABLE:
        if data in _load_used():
            raise BadTap("already used")
        _mark_used(data)
    return int(iid), code
