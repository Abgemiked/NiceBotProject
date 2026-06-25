"""Client für die interne Bot-Service-API (Rollenauflösung).

Spricht GET {BOT_API_URL}/internal/members/{discord_id}/roles mit dem
X-Service-Token an (siehe service_api.py:291). Antwortform:
    {"is_member": bool, "role_ids": [str], "username": str}
"""
import httpx

from .config import settings


class BotApiError(RuntimeError):
    pass


async def fetch_member_roles(discord_id: str):
    """Liefert (is_member, role_ids:list[str], username:str|None).

    Wirft BotApiError bei Auth-/Netzwerk-/Guild-Problemen, damit der Aufrufer
    sauber mit 502/503 antworten kann (statt einen leeren Rollensatz als
    'kein Zugriff' fehlzuinterpretieren).
    """
    url = f"{settings.BOT_API_URL}/internal/members/{discord_id}/roles"
    headers = {"X-Service-Token": settings.BOT_SERVICE_TOKEN}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers)
    except httpx.HTTPError as exc:
        raise BotApiError(f"Bot-API nicht erreichbar: {exc}") from exc

    if resp.status_code == 401:
        raise BotApiError("Service-Token vom Bot abgelehnt")
    if resp.status_code == 503:
        raise BotApiError("Guild/Discord beim Bot nicht verfügbar")
    if resp.status_code != 200:
        raise BotApiError(f"Unerwartete Bot-API-Antwort: HTTP {resp.status_code}")

    try:
        data = resp.json()
    except ValueError as exc:
        raise BotApiError("Bot-API lieferte kein gültiges JSON") from exc
    return (
        bool(data.get("is_member")),
        list(data.get("role_ids") or []),
        data.get("username"),
    )


async def _get_json(path):
    """Generischer authentifizierter GET gegen die Bot-API → JSON-dict."""
    url = f"{settings.BOT_API_URL}{path}"
    headers = {"X-Service-Token": settings.BOT_SERVICE_TOKEN}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers)
    except httpx.HTTPError as exc:
        raise BotApiError(f"Bot-API nicht erreichbar: {exc}") from exc
    if resp.status_code != 200:
        raise BotApiError(f"Bot-API-Fehler ({path}): HTTP {resp.status_code}")
    try:
        return resp.json()
    except ValueError as exc:
        raise BotApiError("Bot-API lieferte kein gültiges JSON") from exc


async def fetch_stats():
    """Holt die Mitglieder-Statistik (Membercount) von der Bot-API."""
    return await _get_json("/internal/stats")


async def fetch_channels():
    """Holt die Guild-Channels (id, name, type) von der Bot-API."""
    return (await _get_json("/internal/channels")).get("channels", [])


async def fetch_roles():
    """Holt die Guild-Rollen (id, name) von der Bot-API."""
    return (await _get_json("/internal/roles")).get("roles", [])
