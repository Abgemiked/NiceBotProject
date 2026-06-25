"""Discord OAuth2 Login/Logout (Authorization Code Flow).

Flow:
  /api/auth/login    → erzeugt CSRF-State (signierte Cookie) + Redirect zu Discord
  /api/auth/callback → prüft State, tauscht Code gegen Token, holt /users/@me,
                       löst Guild-Rollen über die Bot-API auf, setzt Session-Cookie
  /api/auth/logout   → löscht Session-Cookie

Der Discord-Access-Token wird NUR serverseitig benutzt (User-Identität abrufen)
und nie an den Browser weitergegeben oder in der Session gespeichert.
"""
import secrets
import urllib.parse

import httpx
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import RedirectResponse

from ..config import settings
from ..bot_client import fetch_member_roles, BotApiError
from ..rbac import Tier, resolve_tier
from ..session import issue_state, read_state, issue_session

router = APIRouter(prefix="/api/auth", tags=["auth"])

_STATE_COOKIE = "nicebot_admin_oauth_state"


def _cookie_kwargs(max_age):
    return {
        "max_age": max_age,
        "httponly": True,
        "secure": settings.COOKIE_SECURE,
        "samesite": "lax",
        "path": "/",
    }


@router.get("/login")
def login():
    state = secrets.token_urlsafe(24)
    params = {
        "client_id": settings.DISCORD_CLIENT_ID,
        "redirect_uri": settings.OAUTH_REDIRECT_URI,
        "response_type": "code",
        "scope": "identify",
        "state": state,
        "prompt": "none",
    }
    auth_url = f"{settings.DISCORD_API_BASE}/oauth2/authorize?" + urllib.parse.urlencode(params)
    resp = RedirectResponse(auth_url, status_code=302)
    # State signiert in eine kurzlebige Cookie — Abgleich im Callback (CSRF-Schutz).
    resp.set_cookie(_STATE_COOKIE, issue_state(state), **_cookie_kwargs(600))
    return resp


@router.get("/callback")
async def callback(request: Request, code: str = "", state: str = ""):
    expected = read_state(request.cookies.get(_STATE_COOKIE))
    if not expected or not state or not secrets.compare_digest(state, expected):
        raise HTTPException(status_code=400, detail="Ungültiger OAuth-State")
    if not code:
        raise HTTPException(status_code=400, detail="Kein Authorization-Code")

    # 1) Code → Access-Token
    token_data = {
        "client_id": settings.DISCORD_CLIENT_ID,
        "client_secret": settings.DISCORD_CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.OAUTH_REDIRECT_URI,
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        tok = await client.post(
            f"{settings.DISCORD_API_BASE}/oauth2/token",
            data=token_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if tok.status_code != 200:
            raise HTTPException(status_code=401, detail="OAuth-Token-Tausch fehlgeschlagen")
        access_token = tok.json().get("access_token")

        # 2) Identität abrufen
        me = await client.get(
            f"{settings.DISCORD_API_BASE}/users/@me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if me.status_code != 200:
            raise HTTPException(status_code=401, detail="Discord-Identität nicht abrufbar")
        discord_id = me.json().get("id")

    # 3) Guild-Rollen über die Bot-API auflösen (Single Source of Truth)
    try:
        is_member, role_ids, bot_username = await fetch_member_roles(discord_id)
    except BotApiError as exc:
        raise HTTPException(status_code=502, detail=f"Rollenauflösung fehlgeschlagen: {exc}")

    tier = resolve_tier(role_ids, settings.FULL_ADMIN_ROLE_IDS, settings.MOD_ROLE_IDS)
    if not is_member or tier == Tier.NONE:
        raise HTTPException(status_code=403, detail="Keine berechtigte Rolle auf dem Server")

    username = bot_username or me.json().get("username")
    resp = RedirectResponse("/", status_code=302)
    resp.set_cookie(
        settings.SESSION_COOKIE,
        issue_session(discord_id, username, tier.value),
        **_cookie_kwargs(settings.SESSION_MAX_AGE),
    )
    resp.delete_cookie(_STATE_COOKIE, path="/")
    return resp


@router.post("/logout")
def logout(response: Response):
    resp = Response(status_code=204)
    resp.delete_cookie(settings.SESSION_COOKIE, path="/")
    return resp
