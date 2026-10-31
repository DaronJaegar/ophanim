"""'Is this link safe?' (plan check S2). Staff forward a message with a link; we judge it with OFFLINE rules only.
- The link is never opened and the message never goes to the AI or to Ask Sahayak: it is attacker-written.
- The verdict is "be careful" or "looks normal, but I can't be sure". We never say a link is safe.
Not to be confused with the guide id "linkcheck" (how alerts are joined): this module's guide id is "urlcheck"."""
import difflib, ipaddress, re
from urllib.parse import urlsplit

from common.config import VENDOR_DOMAINS

URL_RE = re.compile(r"(?:https?://|www\.)[^\s<>\"'()]+", re.I)
SHORTENERS = {"bit.ly", "tinyurl.com", "t.ly", "cutt.ly", "is.gd", "rb.gy", "shorturl.at", "tiny.cc", "ow.ly",
              "goo.gl", "rebrand.ly", "t.co", "s.id", "shorturl.asia"}
PROGRAMS = (".apk", ".exe", ".scr", ".bat", ".msi", ".js", ".hta", ".vbs", ".cmd", ".jar")
# Real sites that scammers copy most in India, plus the clinic's own vendors (VENDOR_DOMAINS in .env)
KNOWN = {"onlinesbi.sbi", "sbi.co.in", "hdfcbank.com", "icicibank.com", "axisbank.com", "kotak.com", "pnbindia.in",
         "bankofbaroda.in", "paytm.com", "phonepe.com", "npci.org.in", "incometax.gov.in", "gst.gov.in",
         "google.com", "gmail.com", "microsoft.com", "whatsapp.com", "amazon.in", "flipkart.com"}
NAMES = {"sbi": "SBI", "onlinesbi": "SBI", "hdfcbank": "HDFC Bank", "hdfc": "HDFC Bank", "icicibank": "ICICI Bank",
         "icici": "ICICI Bank", "axisbank": "Axis Bank", "kotak": "Kotak Bank", "pnbindia": "PNB", "bankofbaroda": "Bank of Baroda",
         "paytm": "Paytm", "phonepe": "PhonePe", "npci": "NPCI (UPI)", "incometax": "the income tax site", "gst": "the GST site",
         "google": "Google", "gmail": "Gmail", "microsoft": "Microsoft", "whatsapp": "WhatsApp", "amazon": "Amazon",
         "flipkart": "Flipkart"}
TWO_PART = (".co.in", ".gov.in", ".org.in", ".net.in", ".ac.in", ".co.uk")

CAREFUL = "Be careful: don't open this link."
ADVICE = ("If it says it's from your bank or a vendor, don't use the link. Open their app yourself, "
          "or call the number you already have.")
NORMAL = ("I didn't see the usual warning signs in this link, but I can't be sure it's safe.\n"
          "If it asks for a password, OTP or payment, stop and call your IT helper.")


def registered(host):
    """example.co.in from www.login.example.co.in"""
    parts = host.split(".")
    n = 3 if host.endswith(TWO_PART) and len(parts) >= 3 else 2
    return ".".join(parts[-n:])


def known_sites():
    return KNOWN | {d.lower() for d in VENDOR_DOMAINS}


def reasons(url):
    """Plain-word warning signs for one link. Empty list = no sign found (which is NOT 'safe')."""
    u = urlsplit(url if "://" in url else "http://" + url)
    host = (u.hostname or "").lower().rstrip(".")
    out = []
    if "@" in u.netloc:
        out.append("it hides the real address behind an @ sign")
    try:
        ipaddress.ip_address(host)
        out.append("it goes to a number instead of a website name")
    except ValueError:
        pass
    if "xn--" in host:
        out.append("it uses look-alike letters to copy a real name")
    if host in SHORTENERS:
        out.append("it's a short link that hides where it really goes")
    if u.path.lower().endswith(PROGRAMS):
        out.append("it downloads a program or app, which can take over the computer or phone")
    if host and registered(host) not in known_sites():
        for label in re.split(r"[.\-]", host):           # sbi-kyc-update.com, hdfcbnak.com, amazon-offers.xyz
            name = NAMES.get(label) or next((NAMES[n] for n in NAMES if len(n) >= 5 and
                                             difflib.SequenceMatcher(None, label, n).ratio() >= 0.85), None)
            if name:
                out.append(f"it pretends to be {name}, but it isn't their real website")
                break
    return out


def check_text(text):
    """The reply for a message with links. Never opens anything; never says 'safe'."""
    urls = URL_RE.findall(text or "")[:5]
    found = []
    for url in urls:
        for r in reasons(url.rstrip(".,;:!?")):
            if r not in found:
                found.append(r)
    if not found:
        return NORMAL
    return "\n".join([CAREFUL] + [f"• {r}" for r in found[:3]] + [ADVICE])


def has_link(text):
    return bool(URL_RE.search(text or ""))
