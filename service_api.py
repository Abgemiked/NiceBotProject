"""Interner Service-HTTP-Endpoint für das Turnier-Backend (Phase 4).

Das Turnier-Backend (turnier-abgemiked) leitet Website-Rechte aus
Discord-Rollen ab ("Nachtrag 2"). Da nur der Bot in der NiceCom-Guild sitzt,
stellt er hier einen schlanken internen Endpoint bereit:

    GET /internal/members/{discord_id}/roles
    Auth: X-Service-Token  (gleiches Shared Secret wie /verknüpfen,
                            TURNIER_SERVICE_TOKEN)

    200 → {"is_member": true,  "role_ids": ["…"], "username": "…"}
    200 → {"is_member": false, "role_ids": []}        (kein Guild-Mitglied)
    400 → ungültige Discord-ID
    401 → fehlender/falscher Service-Token
    503 → Bot/Guild (noch) nicht bereit

Sicherheit/Betrieb:
- KEIN Host-Port-Mapping — der Endpoint ist nur aus den Docker-Netzen des
  Bots erreichbar (turnier-backend hängt im selben npm-web-Netz).
- Antwortet ausschließlich mit Rollen-IDs (keine Rollennamen, kein PII über
  den Username hinaus, der dem Turnier-Backend ohnehin bekannt ist).
- Port via SERVICE_API_PORT (Default 8130).
"""
import hmac

import discord
from aiohttp import web

DEFAULT_PORT = 8130


def _token_ok(request, expected):
    provided = request.headers.get("X-Service-Token")
    if not expected or not provided:
        return False
    return hmac.compare_digest(provided, expected)


def create_service_app(cfg_json, bot):
    """Baut die aiohttp-App (separat testbar, ohne laufenden Bot)."""

    async def member_roles(request):
        if not _token_ok(request, cfg_json.get("TURNIER_SERVICE_TOKEN")):
            return web.json_response({"error": "Ungültiger Service-Token"}, status=401)

        raw_id = request.match_info.get("discord_id", "")
        if not raw_id.isdigit() or not (5 <= len(raw_id) <= 25):
            return web.json_response({"error": "Ungültige Discord-ID"}, status=400)
        discord_id = int(raw_id)

        guild = bot.get_guild(cfg_json.get("GUILD_ID"))
        if guild is None:
            return web.json_response({"error": "Guild nicht verfügbar"}, status=503)

        member = guild.get_member(discord_id)
        if member is None:
            # Member-Cache kann (z.B. kurz nach Start) unvollständig sein →
            # einmaliger API-Fetch; NotFound = definitiv kein Mitglied.
            try:
                member = await guild.fetch_member(discord_id)
            except discord.NotFound:
                return web.json_response({"is_member": False, "role_ids": []})
            except discord.HTTPException:
                return web.json_response({"error": "Discord nicht erreichbar"}, status=503)

        role_ids = [str(r.id) for r in member.roles if r != guild.default_role]
        return web.json_response(
            {"is_member": True, "role_ids": role_ids, "username": member.name}
        )

    app = web.Application()
    app.router.add_get("/internal/members/{discord_id}/roles", member_roles)
    return app


async def start_service_api(cfg_json, bot):
    """Startet den internen HTTP-Server (idempotent vom Aufrufer zu sichern)."""
    port = int(cfg_json.get("SERVICE_API_PORT") or DEFAULT_PORT)
    runner = web.AppRunner(create_service_app(cfg_json, bot))
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"Service-API gestartet (Port {port})")
    return runner
