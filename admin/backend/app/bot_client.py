"""Client für die interne Bot-Service-API (Rollenauflösung).

Spricht GET {BOT_API_URL}/internal/members/{discord_id}/roles mit dem
X-Service-Token an (siehe service_api.py:291). Antwortform:
    {"is_member": bool, "role_ids": [str], "username": str}
"""
from urllib.parse import quote

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


async def _request(method, path, json_body=None):
    """Authentifizierter Request → (status_code:int, data:dict). Wirft BotApiError
    nur bei Netzwerkfehler/ungültigem JSON, NICHT bei HTTP-Fehlerstatus (damit
    der Aufrufer 404/409 differenziert behandeln kann)."""
    url = f"{settings.BOT_API_URL}{path}"
    headers = {"X-Service-Token": settings.BOT_SERVICE_TOKEN}
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.request(method, url, headers=headers, json=json_body)
    except httpx.HTTPError as exc:
        raise BotApiError(f"Bot-API nicht erreichbar: {exc}") from exc
    try:
        data = resp.json()
    except ValueError:
        data = {}
    return resp.status_code, data


async def fetch_streamers():
    return (await _get_json("/internal/streamers")).get("streamers", [])


async def create_streamer(name):
    return await _request("POST", "/internal/streamers", {"name": name})


async def delete_streamer(name):
    return await _request("DELETE", "/internal/streamers", {"name": name})


async def resolve_names(ids):
    """Löst Discord-IDs zu Anzeigenamen auf (best effort, leeres dict bei Fehler)."""
    if not ids:
        return {}
    try:
        status, data = await _request("POST", "/internal/resolve-names", {"ids": list(ids)})
    except BotApiError:
        return {}
    return data.get("names", {}) if status == 200 else {}


async def fetch_members(search=None, page=1, page_size=25):
    q = []
    if search:
        q.append(f"search={quote(str(search))}")
    q.append(f"page={int(page)}")
    q.append(f"page_size={int(page_size)}")
    return await _get_json("/internal/guild-members?" + "&".join(q))
