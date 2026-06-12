"""Slash-Command /verknüpfen — persönlicher Einmal-Link zum Turnier-Profil.

Ruft die Turnier-Backend-API (turnier-abgemiked) auf:
POST {TURNIER_API_URL}/api/internal/link-tokens  (Auth: X-Service-Token)
und antwortet EPHEMERAL mit dem generierten Link (15 Minuten gültig, einmalig).

Konfiguration (config.json oder ENV, siehe config.py):
- TURNIER_API_URL       Default http://turnier-backend:3130 (Docker-Netz)
- TURNIER_SERVICE_TOKEN Shared Secret — MUSS mit SERVICE_TOKEN der Turnier-.env
                        übereinstimmen (gehört in die nicebot-.env, nicht in config.json)
"""
import asyncio

import aiohttp

DEFAULT_API_URL = "http://turnier-backend:3130"
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=10)
UNAVAILABLE_MSG = "Verknüpfungsdienst nicht erreichbar. Bitte versuche es später erneut."


async def request_link_token(base_url, service_token, discord_id, discord_username):
    """Fordert einen Einmal-Link beim Turnier-Backend an. Liefert die URL oder None."""
    payload = {"discord_id": str(discord_id), "discord_username": discord_username}
    headers = {"X-Service-Token": service_token}
    async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
        async with session.post(
            f"{base_url}/api/internal/link-tokens", json=payload, headers=headers
        ) as response:
            if response.status != 201:
                raise aiohttp.ClientError(f"Turnier-API: HTTP {response.status}")
            data = await response.json()
    return data.get("url")


async def handler(cfg_json, interaction):
    # Ephemeral schon beim defer — der Link ist persönlich und gehört nicht in den Channel
    await interaction.response.defer(ephemeral=True)

    base_url = (cfg_json.get("TURNIER_API_URL") or DEFAULT_API_URL).rstrip("/")
    service_token = cfg_json.get("TURNIER_SERVICE_TOKEN")
    if not service_token:
        await interaction.edit_original_response(content=UNAVAILABLE_MSG)
        return

    try:
        url = await request_link_token(
            base_url, service_token, interaction.user.id, interaction.user.name
        )
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
        await interaction.edit_original_response(content=UNAVAILABLE_MSG)
        return

    if not url:
        await interaction.edit_original_response(content=UNAVAILABLE_MSG)
        return

    await interaction.edit_original_response(
        content=(
            "Dein persönlicher Link zum Turnier-Profil:\n"
            f"{url}\n"
            "-# Der Link ist 15 Minuten gültig und nur einmal verwendbar. Teile ihn mit niemandem."
        )
    )
