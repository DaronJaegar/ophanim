"""Honeytokens (Bruce, Module A). Each decoy contains a link like  http://<brain>:8000/t/<token>.
No real staff member has a reason to open it, so any visit is an intruder."""
import secrets
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from common.config import env

router = APIRouter()
# Fixed tokens from .env so the links you paste into the decoy doc/email keep working after a restart:
# HONEY_TOKENS=decoy-doc:Xq3v9LmP,decoy-email:Tb7wQ2rN   (make your own random strings)
TOKENS = {tok: where for where, tok in (p.split(":", 1) for p in env("HONEY_TOKENS").split(",") if ":" in p)}
PREVIEW_BOTS = ("telegrambot", "whatsapp", "facebookexternalhit", "slackbot", "googlebot", "bingbot", "discordbot")

def new_token(planted_in):
    t = secrets.token_urlsafe(8)
    TOKENS[t] = planted_in
    return t

LOGIN_PAGE = """<html><body style="font-family:sans-serif;max-width:360px;margin:60px auto">
<h3>Net banking login</h3><input placeholder="Customer ID"><br><br><input type="password" placeholder="Password">
<br><br><button>Login</button></body></html>"""      # generic page: no real bank's name or logo

@router.get("/t/{token}", response_class=HTMLResponse)
def hit(token: str, request: Request):
    ua = request.headers.get("user-agent", "").lower()
    if token in TOKENS and not any(b in ua for b in PREVIEW_BOTS):
        from brain.app import post_event, Event
        post_event(Event(source="honeytoken", type="honeytoken_hit", entity="honeytoken:" + token,
                         evidence={"planted_in": TOKENS[token], "ip": request.client.host if request.client else "",
                                   "user_agent": ua[:120]}))
    return LOGIN_PAGE
