"""Multi-marker scoring for Gmail filters (Aaron, Module B).
No single marker is enough; markers add up. >=5 alert now, 3-4 ask the owner, <3 weekly digest.
"""
MONEY_WORDS = ["invoice", "payment", "bank", "upi", "ifsc", "account", "transfer", "salary", "neft", "rtgs",
               "gst", "remittance", "beneficiary", "kyc", "cheque", "a/c", "swift", "imps", "payout"]
# not "refund": archiving shop refund mail (from:refunds@amazon.in, skip inbox) would become an "ask" false alarm
SECURITY_WORDS = ["security", "password", "otp", "verify", "verification", "sign-in", "signin",
                  "login", "alert", "accounts.google.com", "no-reply@accounts.google.com", "2-step",
                  "2fa", "two-step", "recovery", "new device", "suspicious", "unusual activity"]
# not bare "google.com": "from:calendar-notification@google.com, skip inbox" is a normal rule
HIDE_LABELS_ADD = {"TRASH", "SPAM"}
HIDE_LABELS_REMOVE = {"INBOX", "UNREAD"}
# Free mailboxes that hide who owns them: a forward there adds +1 on top of "sends mail outside"
ANON_MAIL = ("proton.me", "protonmail.com", "tutanota.com", "tuta.io", "mail.ru", "yandex.com", "yandex.ru",
             "guerrillamail.com", "cock.li", "onionmail.org")

def _criteria_text(f):
    c = f.get("criteria", {})
    return " ".join(str(c.get(k, "")) for k in ("from", "to", "subject", "query")).lower()

def score_filter(f, clinic_domain="gmail.com", recent_change=False, vendor_domains=None):
    """f is a Gmail filter dict exactly as the Gmail API returns it.
    vendor_domains: the clinic's vendors' email domains (VENDOR_DOMAINS in .env); None = from config."""
    if vendor_domains is None:
        from common.config import VENDOR_DOMAINS as vendor_domains
    markers, score = [], 0
    action = f.get("action", {})
    text = _criteria_text(f)
    crit = f.get("criteria", {})

    fwd = action.get("forward")
    if fwd and not fwd.lower().endswith("@" + clinic_domain.lower()):
        markers.append("sends mail outside"); score += 3
    elif fwd and clinic_domain.lower() in ("gmail.com", "googlemail.com"):
        # personal Gmail: every forward goes to another person's account
        markers.append("sends mail to another account"); score += 3
    if fwd and fwd.lower().rsplit("@", 1)[-1] in ANON_MAIL:
        markers.append("forwards to an anonymous mailbox"); score += 1

    hides = HIDE_LABELS_ADD & set(action.get("addLabelIds", [])) or \
        HIDE_LABELS_REMOVE & set(action.get("removeLabelIds", []))
    if hides:
        markers.append("hides mail"); score += 2

    sender = str(crit.get("from", "")).lower()
    words = any(w in text for w in MONEY_WORDS + SECURITY_WORDS)
    if sender and any(sender.endswith(d.lower()) for d in vendor_domains or ()):
        markers.append("targets a vendor's email"); score += 2     # in place of the word marker, never both
    elif words:
        markers.append("targets money or security words"); score += 2

    # Skip the inbox AND mark as read: the reply never shows up as new. Only with money/security words,
    # because newsletters do this too (from:linkedin.com -> skip inbox + read is in our normal eval set).
    if words and HIDE_LABELS_REMOVE <= set(action.get("removeLabelIds", [])):
        markers.append("hides and marks as read"); score += 1

    if fwd and (sender in ("me", "me@" + clinic_domain.lower()) or "in:sent" in text or "from:me" in text):
        markers.append("copies mail the clinic sends"); score += 2

    if not any(crit.values()) or (crit.get("query") and len(crit["query"].strip()) <= 2):
        markers.append("matches almost every email"); score += 1

    if recent_change:
        markers.append("other risky change in the last 24 h"); score += 2

    level = "alert" if score >= 5 else ("ask" if score >= 3 else "digest")
    return {"score": score, "markers": markers, "level": level}
