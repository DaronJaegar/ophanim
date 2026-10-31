"""Shared settings. Every module reads its settings from here (values come from .env)."""
import os
from dotenv import load_dotenv

load_dotenv()

def env(name, default=""):
    return os.getenv(name, default).split("#")[0].strip()

BRAIN_URL = env("BRAIN_URL", "http://127.0.0.1:8000")
BRAIN_IP = env("BRAIN_IP", "127.0.0.1")
CLINIC_DOMAIN = env("CLINIC_DOMAIN", "gmail.com")
VENDOR_DOMAINS = [d.strip().lower() for d in env("VENDOR_DOMAINS").split(",") if d.strip()]   # e.g. supplier.in,bank.in
CLINIC_EMAIL = env("CLINIC_EMAIL", "")
POLL_SECONDS = int(env("POLL_SECONDS", "30") or 30)
TELEGRAM_TOKEN = env("TELEGRAM_TOKEN")
OWNER_CHAT_ID = env("OWNER_CHAT_ID")
STAFF_CHAT_IDS = [c for c in env("STAFF_CHAT_IDS").split(",") if c]
VENDOR_CHAT_IDS = dict(p.split(":", 1) for p in env("VENDOR_CHAT_IDS").split(",") if ":" in p)
SECURITY_CODE = env("SECURITY_CODE", "MANGO-42")
CHAT_LANGS = dict(p.split(":", 1) for p in env("CHAT_LANGS").split(",") if ":" in p)   # chat_id:kn,chat_id:en
HMAC_SECRET = env("HMAC_SECRET", "dev-secret-change-me")      # no '#' in it: env() cuts at '#'
IT_CHAT_ID = env("IT_CHAT_ID")                                  # optional: IT helper's Telegram chat id
CLINIC_NAME = env("CLINIC_NAME", "Sunrise Clinic")
USED_TAPS_FILE = env("USED_TAPS_FILE", ".sahayak_used_taps")    # one-time taps survive a bot restart
LLM_BASE_URL = env("LLM_BASE_URL")
LLM_API_KEY = env("LLM_API_KEY")
LLM_MODEL = env("LLM_MODEL")
DEVICE_ID = env("DEVICE_ID", "frontdesk-pc")
WATCH_DIR = env("WATCH_DIR", "./ClinicFiles")
DRY_RUN = env("DRY_RUN", "1") == "1"
AGENT_TOKEN = env("AGENT_TOKEN")                       # same value on brain + agent; empty = not checked
BRAIN_TOKEN = env("BRAIN_TOKEN")                       # same value on brain + sensors + bot; empty = not checked


def brain_headers():
    """Header for POST /actions and non-agent POST /events when BRAIN_TOKEN is set."""
    return {"X-Brain-Token": BRAIN_TOKEN} if BRAIN_TOKEN else {}


SUSPEND = env("SUSPEND", "1") == "1"                    # agent: freeze the process doing the writing
SIGNAL_METER = env("SIGNAL_METER", "1") == "1"          # agent: live 3-dot signal line in the terminal
RANSOM_NOTES = env("RANSOM_NOTES", "0") == "1"          # agent: a ransom-note file name is a 4th sign (off until after Gate 2)
PC_HEALTH = env("PC_HEALTH", "0") == "1"                # agent (Windows): report virus protection + update age (off until after Gate 2)

# Who uses what (from the onboarding chat). Used by correlation.
PEOPLE = {
    "priya": {"accounts": ["gmail:clinic"], "devices": ["frontdesk-pc"]},
}
