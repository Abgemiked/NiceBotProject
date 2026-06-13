"""Gemeinsame Bausteine für die Turnier-Slash-Commands (Stage D).

Prinzip (siehe PLAN_2026-06-13_staged_slash.md):
  - Read/Info/Liste/Hilfe  → inline ephemeral, Daten aus dem Turnier-Backend
  - Auth-pflichtige Aktion  → personalisierter Website-Deeplink (Link-Token mit
    redirect_path), KEINE Duplizierung der komplexen Flows im Bot.

Rollenprüfung läuft über die Discord-Rollen des aufrufenden Members
(interaction.user.roles) gegen die bekannten NiceCom-Rollen-IDs.

Konfiguration (config.json / ENV, siehe config.py):
  - TURNIER_API_URL        Default http://turnier-backend:3130 (Docker-Netz)
  - TURNIER_SERVICE_TOKEN  Shared Secret (gehört in die .env, NICHT config.json)
  - TURNIER_PUBLIC_URL     Öffentliche Website-Basis (Default
                           https://turnier.abgemiked.de) — nur für Anzeige-Links
                           ohne Login (z.B. /t/:slug in Embeds).
  - TURNIER_EM_ROLE_ID / TURNIER_ADMIN_ROLE_IDS / TURNIER_CASTER_ROLE_ID
                           überschreibbar; Defaults = reale NiceCom-Rollen-IDs.
"""
import asyncio

import aiohttp

DEFAULT_API_URL = "http://turnier-backend:3130"
DEFAULT_PUBLIC_URL = "https://turnier.abgemiked.de"
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=10)

# Reale NiceCom-Rollen-IDs (keine Secrets) — per config überschreibbar.
DEFAULT_EM_ROLE_ID = 1128924760642965564
DEFAULT_ADMIN_ROLE_IDS = (1130018862990098463, 669879940296081420)
DEFAULT_CASTER_ROLE_ID = 1138605333867147396

# Nutzer-sichtbare Standardmeldungen
UNAVAILABLE_MSG = "Turnier-Dienst nicht erreichbar. Bitte versuche es später erneut."
NOT_FOUND_MSG = "Turnier nicht gefunden. Prüfe Name oder Slug mit `/turniere`."
NO_LINK_MSG = (
    "Du bist noch nicht mit dem Turniersystem verknüpft — nutze zuerst "
    "`/verknüpfen` oder den Anmelde-Link."
)


def get_base_url(cfg_json):
    return (cfg_json.get("TURNIER_API_URL") or DEFAULT_API_URL).rstrip("/")


def get_public_url(cfg_json):
    return (cfg_json.get("TURNIER_PUBLIC_URL") or DEFAULT_PUBLIC_URL).rstrip("/")


def get_service_token(cfg_json):
    return cfg_json.get("TURNIER_SERVICE_TOKEN")


# ----- Rollenprüfung (über die Guild-Rollen des aufrufenden Members) -----

def _role_ids(member):
    """Set der Rollen-IDs des Members (robust gegen fehlende .roles)."""
    roles = getattr(member, "roles", None) or []
    return {getattr(r, "id", None) for r in roles}


def _em_role_id(cfg_json):
    return int(cfg_json.get("TURNIER_EM_ROLE_ID") or DEFAULT_EM_ROLE_ID)


def _admin_role_ids(cfg_json):
    raw = cfg_json.get("TURNIER_ADMIN_ROLE_IDS")
    if not raw:
        return set(DEFAULT_ADMIN_ROLE_IDS)
    if isinstance(raw, (list, tuple)):
        return {int(x) for x in raw}
    return {int(raw)}


def _caster_role_id(cfg_json):
    return int(cfg_json.get("TURNIER_CASTER_ROLE_ID") or DEFAULT_CASTER_ROLE_ID)


def is_admin(cfg_json, member):
    return bool(_role_ids(member) & _admin_role_ids(cfg_json))


def is_eventmanager(cfg_json, member):
    return _em_role_id(cfg_json) in _role_ids(member)


def is_caster(cfg_json, member):
    return _caster_role_id(cfg_json) in _role_ids(member)


def is_em_or_admin(cfg_json, member):
    """EM-Befehle: Eventmanagement ODER Admin dürfen ran."""
    return is_eventmanager(cfg_json, member) or is_admin(cfg_json, member)


# ----- Deeplink-Erzeugung (Login-Token mit Ziel-Pfad) -----

async def request_deeplink(base_url, service_token, discord_id, discord_username, redirect_path=None):
    """Fordert einen personalisierten Einmal-Login-Link an, der nach dem Login
    auf ``redirect_path`` weiterleitet. Liefert die URL oder wirft ClientError."""
    payload = {"discord_id": str(discord_id), "discord_username": discord_username}
    if redirect_path:
        payload["redirect_path"] = redirect_path
    headers = {"X-Service-Token": service_token}
    async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
        async with session.post(
            f"{base_url}/api/internal/link-tokens", json=payload, headers=headers
        ) as response:
            if response.status != 201:
                raise aiohttp.ClientError(f"Turnier-API: HTTP {response.status}")
            data = await response.json()
    return data.get("url")


# ----- Backend-GET-Helfer (Service-Token) -----

async def _get_json(base_url, service_token, path, params=None):
    """GET gegen das Turnier-Backend. Liefert (status, json|None)."""
    headers = {"X-Service-Token": service_token}
    async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
        async with session.get(
            f"{base_url}{path}", headers=headers, params=params
        ) as response:
            if response.status >= 500:
                raise aiohttp.ClientError(f"Turnier-API: HTTP {response.status}")
            try:
                data = await response.json()
            except (aiohttp.ContentTypeError, ValueError):
                data = None
            return response.status, data


async def fetch_tournaments(base_url, service_token):
    status, data = await _get_json(base_url, service_token, "/api/internal/bot/tournaments")
    if status != 200 or not data:
        raise aiohttp.ClientError(f"Turnier-API: HTTP {status}")
    return data.get("tournaments", [])


async def fetch_tournament(base_url, service_token, slug_or_name):
    """Kurz-Info zu einem Turnier. Liefert dict oder None (404)."""
    from urllib.parse import quote
    path = f"/api/internal/bot/tournament/{quote(slug_or_name, safe='')}"
    status, data = await _get_json(base_url, service_token, path)
    if status == 404:
        return None
    if status != 200 or not data:
        raise aiohttp.ClientError(f"Turnier-API: HTTP {status}")
    return data.get("tournament")


async def fetch_my_teams(base_url, service_token, discord_id):
    status, data = await _get_json(
        base_url, service_token, "/api/internal/bot/my-teams",
        params={"discord_id": str(discord_id)},
    )
    if status != 200 or not data:
        raise aiohttp.ClientError(f"Turnier-API: HTTP {status}")
    return data.get("teams", [])


# ----- Anzeige-Helfer -----

STATUS_LABEL = {
    "draft": "Entwurf",
    "registration": "Anmeldung offen",
    "running": "läuft",
    "completed": "abgeschlossen",
    "cancelled": "abgesagt",
}


def status_label(status):
    return STATUS_LABEL.get(status, status)


def public_tournament_url(cfg_json, slug):
    return f"{get_public_url(cfg_json)}/t/{slug}"


# Sammelfehler für die Command-Handler — fängt Backend-Ausfall + Timeout ab.
BACKEND_ERRORS = (aiohttp.ClientError, asyncio.TimeoutError, ValueError)
