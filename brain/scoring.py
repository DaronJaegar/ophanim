"""Multi-marker scoring for Gmail filters (Aaron, Module B).
No single marker is enough; markers add up. >=5 alert now, 3-4 ask the owner, <3 weekly digest.
"""
MONEY_WORDS = ["invoice", "payment", "bank", "upi", "ifsc", "account", "transfer", "salary", "neft", "rtgs"]
SECURITY_WORDS = ["security", "password", "otp", "verify", "verification", "sign-in", "signin",
                  "login", "alert", "accounts.google.com", "no-reply@accounts.google.com", "2-step"]
HIDE_LABELS_ADD = {"TRASH", "SPAM"}
HIDE_LABELS_REMOVE = {"INBOX", "UNREAD"}

def _criteria_text(f):
    c = f.get("criteria", {})
    return " ".join(str(c.get(k, "")) for k in ("from", "to", "subject", "query")).lower()

def score_filter(f, clinic_domain="gmail.com", recent_change=False):
    """f is a Gmail filter dict exactly as the Gmail API returns it."""
    markers, score = [], 0
    action = f.get("action", {})
    text = _criteria_text(f)

    fwd = action.get("forward")
    if fwd and not fwd.lower().endswith("@" + clinic_domain.lower()):
        markers.append("sends mail outside"); score += 3
    elif fwd and clinic_domain.lower() in ("gmail.com", "googlemail.com"):
        # personal Gmail: every forward goes to another person's account
        markers.append("sends mail to another account"); score += 3

    if HIDE_LABELS_ADD & set(action.get("addLabelIds", [])) or \
       HIDE_LABELS_REMOVE & set(action.get("removeLabelIds", [])):
        markers.append("hides mail"); score += 2

    if any(w in text for w in MONEY_WORDS + SECURITY_WORDS):
        markers.append("targets money or security words"); score += 2

    crit = f.get("criteria", {})
    if not any(crit.values()) or (crit.get("query") and len(crit["query"].strip()) <= 2):
        markers.append("matches almost every email"); score += 1

    if recent_change:
        markers.append("other risky change in the last 24 h"); score += 2

    level = "alert" if score >= 5 else ("ask" if score >= 3 else "digest")
    return {"score": score, "markers": markers, "level": level}
