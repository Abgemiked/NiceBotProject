"""Interner Service-HTTP-Endpoint für das Turnier-Backend (Phase 4 + 7).

Das Turnier-Backend (turnier-abgemiked) leitet Website-Rechte aus
Discord-Rollen ab ("Nachtrag 2"). Da nur der Bot in der NiceCom-Guild sitzt,
stellt er hier schlanke interne Endpoints bereit:

    GET /internal/members/{discord_id}/roles
    Auth: X-Service-Token  (gleiches Shared Secret wie /verknüpfen,
                            TURNIER_SERVICE_TOKEN)

    200 → {"is_member": true,  "role_ids": ["…"], "username": "…"}
    200 → {"is_member": false, "role_ids": []}        (kein Guild-Mitglied)
    400 → ungültige Discord-ID
    401 → fehlender/falscher Service-Token
    503 → Bot/Guild (noch) nicht bereit

Phase 7 Stage A — Turnier-Artefakte (Kategorie + Channels + Webhook):

    POST /internal/tournaments/discord
        Body: {"tournament_name": "…", "slug": "…", "overview_url": "https://…"}
        201 → {"category_id", "participant_role_id", "news_channel_id",
               "eventfeed_channel_id", "overview_channel_id",
               "webhook_id", "webhook_url"}
        502 → {"error": "…", "created": {…}}  (Teilzustand wird IMMER
               zurückgegeben, damit das Backend ihn speichern/aufräumen kann)

    DELETE /internal/tournaments/discord
        Body: {"category_id": "…", "channel_ids": ["…"], "webhook_id": "…",
               "participant_role_id": "…"}
        Löscht AUSSCHLIESSLICH die übergebenen IDs (kein Lösch-Scan, nie
        nach Namen). Bereits gelöschte Artefakte (404) werden toleriert.
        200 → {"deleted": […], "missing": […]}
        502 → {"deleted": […], "missing": […], "errors": […]}

Phase 7 Stage A.5 — Teilnehmer-Rolle (Sichtbarkeits-Modell):

    Pro Turnier eine Rolle "turnierteilnehmer-[Name]" (mentionable=False).
    Sichtbarkeit:
      - Kategorie:           @everyone sichtbar, read-only; EM volle Rechte
      - turnier-uebersicht:  erbt Kategorie (alle sehen, nur EM/Bot posten)
      - teilnehmer-infos:    @everyone unsichtbar; Teilnehmer-Rolle liest;
                             EM volle Rechte
      - em-eventfeed:        NUR EM/Bot/Webhook (Teilnehmer sehen ihn nicht);
                             EM volle Rechte + Webhook

    POST /internal/tournaments/discord/role-assign
        Body: {"role_id": "…", "discord_id": "…"}  → member.add_roles
    POST /internal/tournaments/discord/role-remove
        Body: {"role_id": "…", "discord_id": "…"}  → member.remove_roles
    Beide 404-tolerant (Rolle/Member weg → klare Meldung, kein Crash).
    Defense-in-Depth (Audit A.5/F1): Beide Endpoints akzeptieren NUR Rollen,
    deren Name mit PARTICIPANT_ROLE_PREFIX beginnt — bei einem Token-Leck
    kann niemand EM-/Mod-/sonstige Rollen vergeben oder entziehen (403).
    Zusätzlich 403, wenn die Rolle >= Bot-Top-Rolle liegt (vom Bot ohnehin
    nicht verwaltbar — klare Meldung statt Discord-Forbidden).

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

# Eventmanagement-Rolle auf der NiceCom-Guild (überschreibbar via
# TURNIER_EM_ROLE_ID in config.json/.env). Bekommt volle Rechte auf der
# Turnier-Kategorie; Channels erben über die Kategorie-Overwrites.
DEFAULT_EM_ROLE_ID = 1128924760642965564

# Discord-Limits
MAX_CHANNEL_NAME = 100
MAX_TOPIC = 1024

# Standard-Channels einer Turnier-Kategorie (Stage A)
NEWS_CHANNEL_NAME = "teilnehmer-infos"
EVENTFEED_CHANNEL_NAME = "em-eventfeed"
OVERVIEW_CHANNEL_NAME = "turnier-uebersicht"
WEBHOOK_NAME = "EM-Feed"

# Stage A.5: Teilnehmer-Rolle je Turnier (Discord-Limit: Rollenname ≤100)
PARTICIPANT_ROLE_PREFIX = "turnierteilnehmer-"


def _full_access_overwrite():
    """Volle Rechte für EM-Rolle/Bot auf Kategorie-Ebene (Channels erben)."""
    return discord.PermissionOverwrite(
        view_channel=True,
        send_messages=True,
        manage_channels=True,
        manage_messages=True,
        manage_webhooks=True,
        read_message_history=True,
        connect=True,
        speak=True,
    )


def _read_only_overwrite():
    """Sichtbar, aber nicht schreibbar (Kategorie-Default für @everyone)."""
    return discord.PermissionOverwrite(view_channel=True, send_messages=False)


def _valid_snowflake(value):
    return isinstance(value, str) and value.isdigit() and 5 <= len(value) <= 25


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

    async def create_tournament_discord(request):
        """Kategorie + Standard-Channels + Webhook für ein Turnier anlegen.

        Idempotenz liegt beim Backend (DB-Artefakt-Zeile prüfen, bevor es
        hierher kommt). Bot-seitig defensiv: bei Discord-Fehlern wird der
        bereits angelegte Teilzustand in "created" zurückgegeben — KEIN
        stiller Teilzustand.
        """
        if not _token_ok(request, cfg_json.get("TURNIER_SERVICE_TOKEN")):
            return web.json_response({"error": "Ungültiger Service-Token"}, status=401)

        try:
            body = await request.json()
        except Exception:
            return web.json_response({"error": "Ungültiger JSON-Body"}, status=400)
        if not isinstance(body, dict):
            return web.json_response({"error": "Ungültiger JSON-Body"}, status=400)

        name = body.get("tournament_name")
        overview_url = body.get("overview_url")
        if not isinstance(name, str) or not name.strip():
            return web.json_response({"error": "tournament_name ist Pflicht"}, status=400)
        if overview_url is not None and (
            not isinstance(overview_url, str) or not overview_url.startswith("https://")
        ):
            return web.json_response(
                {"error": "overview_url muss eine https-URL sein"}, status=400
            )
        category_name = name.strip()[:MAX_CHANNEL_NAME]

        guild = bot.get_guild(cfg_json.get("GUILD_ID"))
        if guild is None:
            return web.json_response({"error": "Guild nicht verfügbar"}, status=503)

        em_role_id = int(cfg_json.get("TURNIER_EM_ROLE_ID") or DEFAULT_EM_ROLE_ID)
        em_role = guild.get_role(em_role_id)
        if em_role is None:
            return web.json_response(
                {"error": f"EM-Rolle {em_role_id} nicht auf der Guild gefunden"},
                status=503,
            )

        full = _full_access_overwrite()
        # Sichtbarkeits-Modell (Stage A.5):
        # Kategorie: @everyone sichtbar aber read-only; EM-Rolle + Bot volle
        # Rechte. turnier-uebersicht erbt diese Overwrites 1:1 (synced).
        category_overwrites = {
            em_role: full,
            guild.me: full,
            guild.default_role: _read_only_overwrite(),
        }

        created = {}
        try:
            category = await guild.create_category(
                category_name, overwrites=category_overwrites,
                reason=f"Turnier-Automatisierung: {category_name}",
            )
            created["category_id"] = str(category.id)

            # Teilnehmer-Rolle: wird bei An-/Abmeldung vom Backend vergeben/
            # entzogen (role-assign/role-remove). NACH der Kategorie angelegt,
            # damit ein Teilzustand immer per category_id im Backend landet.
            role_name = (PARTICIPANT_ROLE_PREFIX + category_name)[:MAX_CHANNEL_NAME]
            participant_role = await guild.create_role(
                name=role_name,
                mentionable=False,
                hoist=False,
                reason=f"Turnier-Automatisierung: Teilnehmer-Rolle {category_name}",
            )
            created["participant_role_id"] = str(participant_role.id)

            # Nur-Teilnehmer-Channels: @everyone unsichtbar, Teilnehmer-Rolle
            # liest (kein Schreiben), EM/Bot volle Rechte.
            participants_only = {
                em_role: full,
                guild.me: full,
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                participant_role: discord.PermissionOverwrite(
                    view_channel=True, send_messages=False
                ),
            }

            # EM-only-Channel: @everyone unsichtbar, KEINE Teilnehmer-Rolle —
            # nur EM/Bot sehen+schreiben (+ Webhook).
            em_only = {
                em_role: full,
                guild.me: full,
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
            }

            # News (teilnehmer-infos): nur Teilnehmer lesen, nur EM/Bot schreiben
            news = await guild.create_text_channel(
                NEWS_CHANNEL_NAME,
                category=category,
                overwrites=participants_only,
                reason="Turnier-Automatisierung: Teilnehmer-Infos",
            )
            created["news_channel_id"] = str(news.id)

            # EM-Eventfeed: NUR EM/Bot/Webhook — Teilnehmer sehen ihn NICHT
            eventfeed = await guild.create_text_channel(
                EVENTFEED_CHANNEL_NAME,
                category=category,
                overwrites=em_only,
                reason="Turnier-Automatisierung: EM-Eventfeed",
            )
            created["eventfeed_channel_id"] = str(eventfeed.id)

            # Übersicht: erbt die Kategorie-Overwrites (alle sehen, read-only),
            # Topic + Pin mit Link zur Live-Seite
            topic = (
                f"Turnier-Übersicht: {overview_url}"[:MAX_TOPIC] if overview_url else None
            )
            overview = await guild.create_text_channel(
                OVERVIEW_CHANNEL_NAME,
                category=category,
                topic=topic,
                overwrites=dict(category_overwrites),
                reason="Turnier-Automatisierung: Übersicht",
            )
            created["overview_channel_id"] = str(overview.id)
            if overview_url:
                try:
                    # allowed_mentions=none(): Der Turniername ist User-Input —
                    # ein Name wie "@everyone Cup" darf NIEMALS die Guild pingen
                    # (Audit M2). Gilt für JEDE Nachricht mit Turnier-/User-Text.
                    msg = await overview.send(
                        f"**{category_name}** — Übersicht & Live-Bracket:\n{overview_url}",
                        allowed_mentions=discord.AllowedMentions.none(),
                    )
                    await msg.pin(reason="Turnier-Übersicht-Link")
                except discord.HTTPException:
                    pass  # Pin ist nice-to-have, kein Abbruchgrund

            webhook = await eventfeed.create_webhook(
                name=WEBHOOK_NAME, reason="Turnier-Automatisierung: EM-Feed-Webhook"
            )
            created["webhook_id"] = str(webhook.id)
            created["webhook_url"] = webhook.url
        except discord.Forbidden:
            return web.json_response(
                {"error": "Discord verweigert die Aktion (fehlende Bot-Rechte)",
                 "created": created},
                status=502,
            )
        except discord.HTTPException as exc:
            return web.json_response(
                {"error": f"Discord-Fehler: {exc}", "created": created}, status=502
            )

        return web.json_response(created, status=201)

    async def delete_tournament_discord(request):
        """Löscht AUSSCHLIESSLICH die übergebenen Artefakt-IDs.

        Tolerant gegen bereits Gelöschtes (404 → "missing"). Es wird nie
        nach Namen gesucht oder breit gelöscht — die ID-Liste kommt aus der
        Artefakt-Tabelle des Backends.
        """
        if not _token_ok(request, cfg_json.get("TURNIER_SERVICE_TOKEN")):
            return web.json_response({"error": "Ungültiger Service-Token"}, status=401)

        try:
            body = await request.json()
        except Exception:
            return web.json_response({"error": "Ungültiger JSON-Body"}, status=400)
        if not isinstance(body, dict):
            return web.json_response({"error": "Ungültiger JSON-Body"}, status=400)

        category_id = body.get("category_id")
        webhook_id = body.get("webhook_id")
        participant_role_id = body.get("participant_role_id")
        raw_channel_ids = body.get("channel_ids") or []
        if not isinstance(raw_channel_ids, list):
            return web.json_response({"error": "channel_ids muss eine Liste sein"}, status=400)
        for value in [category_id, webhook_id, participant_role_id, *raw_channel_ids]:
            if value is not None and not _valid_snowflake(value):
                return web.json_response(
                    {"error": f"Ungültige Discord-ID: {value!r}"}, status=400
                )

        guild = bot.get_guild(cfg_json.get("GUILD_ID"))
        if guild is None:
            return web.json_response({"error": "Guild nicht verfügbar"}, status=503)

        deleted, missing, errors = [], [], []

        async def delete_channel_like(snowflake, label):
            channel = guild.get_channel(int(snowflake))
            if channel is None:
                try:
                    channel = await bot.fetch_channel(int(snowflake))
                except discord.NotFound:
                    missing.append(snowflake)
                    return
                except discord.HTTPException as exc:
                    errors.append(f"{label} {snowflake}: {exc}")
                    return
            # Sicherheitsnetz: nur Channels DIESER Guild anfassen
            if getattr(channel, "guild", None) is None or channel.guild.id != guild.id:
                errors.append(f"{label} {snowflake}: gehört nicht zur NiceCom-Guild")
                return
            try:
                await channel.delete(reason="Turnier-Automatisierung: Cleanup")
                deleted.append(snowflake)
            except discord.NotFound:
                missing.append(snowflake)
            except discord.Forbidden:
                errors.append(f"{label} {snowflake}: fehlende Rechte")
            except discord.HTTPException as exc:
                errors.append(f"{label} {snowflake}: {exc}")

        if webhook_id:
            try:
                webhook = await bot.fetch_webhook(int(webhook_id))
                if webhook.guild_id == guild.id:
                    await webhook.delete(reason="Turnier-Automatisierung: Cleanup")
                    deleted.append(webhook_id)
                else:
                    errors.append(f"Webhook {webhook_id}: gehört nicht zur NiceCom-Guild")
            except discord.NotFound:
                missing.append(webhook_id)
            except discord.Forbidden:
                errors.append(f"Webhook {webhook_id}: fehlende Rechte")
            except discord.HTTPException as exc:
                errors.append(f"Webhook {webhook_id}: {exc}")

        for channel_id in raw_channel_ids:
            await delete_channel_like(channel_id, "Channel")
        if category_id:
            await delete_channel_like(category_id, "Kategorie")

        # Teilnehmer-Rolle (Stage A.5): guild.get_role ist per Konstruktion
        # auf DIESE Guild beschränkt; nicht (mehr) vorhandene Rolle → missing.
        if participant_role_id:
            role = guild.get_role(int(participant_role_id))
            if role is None:
                missing.append(participant_role_id)
            else:
                try:
                    await role.delete(reason="Turnier-Automatisierung: Cleanup")
                    deleted.append(participant_role_id)
                except discord.NotFound:
                    missing.append(participant_role_id)
                except discord.Forbidden:
                    errors.append(f"Rolle {participant_role_id}: fehlende Rechte")
                except discord.HTTPException as exc:
                    errors.append(f"Rolle {participant_role_id}: {exc}")

        payload = {"deleted": deleted, "missing": missing}
        if errors:
            payload["errors"] = errors
            return web.json_response(payload, status=502)
        return web.json_response(payload)

    async def _resolve_role_member(request):
        """Gemeinsame Validierung für role-assign/role-remove.

        Liefert (role, member, None) oder (None, None, Fehler-Response).
        404-tolerant: Rolle/Member nicht (mehr) vorhanden → klare Meldung,
        kein Crash — das Backend behandelt Rollen-Sync als best effort.
        """
        if not _token_ok(request, cfg_json.get("TURNIER_SERVICE_TOKEN")):
            return None, None, web.json_response(
                {"error": "Ungültiger Service-Token"}, status=401
            )
        try:
            body = await request.json()
        except Exception:
            return None, None, web.json_response(
                {"error": "Ungültiger JSON-Body"}, status=400
            )
        if not isinstance(body, dict):
            return None, None, web.json_response(
                {"error": "Ungültiger JSON-Body"}, status=400
            )
        role_id = body.get("role_id")
        discord_id = body.get("discord_id")
        if not _valid_snowflake(role_id) or not _valid_snowflake(discord_id):
            return None, None, web.json_response(
                {"error": "role_id und discord_id müssen gültige Discord-IDs sein"},
                status=400,
            )

        guild = bot.get_guild(cfg_json.get("GUILD_ID"))
        if guild is None:
            return None, None, web.json_response(
                {"error": "Guild nicht verfügbar"}, status=503
            )

        # Guild-Scope: get_role kennt nur Rollen DIESER Guild
        role = guild.get_role(int(role_id))
        if role is None:
            return None, None, web.json_response(
                {"error": f"Rolle {role_id} existiert nicht (mehr) auf der Guild"},
                status=404,
            )

        # Defense-in-Depth (Audit A.5/F1): NUR Teilnehmer-Rollen sind über
        # diese Endpoints verwaltbar. Ohne diesen Guard könnte ein geleakter
        # Service-Token jedem Member jede Rolle (EM/Mod/…) geben/entziehen.
        if not role.name.startswith(PARTICIPANT_ROLE_PREFIX):
            return None, None, web.json_response(
                {
                    "error": (
                        f"Rolle {role_id} ist keine Turnier-Teilnehmer-Rolle "
                        f"(Name muss mit '{PARTICIPANT_ROLE_PREFIX}' beginnen) "
                        "— Zuweisung/Entzug verweigert"
                    )
                },
                status=403,
            )

        # Sicherheits-Guard: Rollen auf/über der Bot-Top-Rolle kann der Bot
        # ohnehin nicht verwalten → klare 403 statt Discord-Forbidden.
        if guild.me is not None and role >= guild.me.top_role:
            return None, None, web.json_response(
                {
                    "error": (
                        f"Rolle {role_id} liegt auf/über der Bot-Rolle "
                        "und kann nicht verwaltet werden"
                    )
                },
                status=403,
            )

        member = guild.get_member(int(discord_id))
        if member is None:
            try:
                member = await guild.fetch_member(int(discord_id))
            except discord.NotFound:
                return None, None, web.json_response(
                    {"error": f"User {discord_id} ist kein Guild-Mitglied (mehr)"},
                    status=404,
                )
            except discord.HTTPException:
                return None, None, web.json_response(
                    {"error": "Discord nicht erreichbar"}, status=503
                )
        return role, member, None

    async def assign_participant_role(request):
        """Teilnehmer-Rolle vergeben (idempotent — add_roles doppelt ist ok)."""
        role, member, error = await _resolve_role_member(request)
        if error is not None:
            return error
        try:
            await member.add_roles(role, reason="Turnier-Automatisierung: Teilnehmer")
        except discord.NotFound:
            return web.json_response(
                {"error": "Rolle oder Member wurde zwischenzeitlich entfernt"}, status=404
            )
        except discord.Forbidden:
            return web.json_response(
                {"error": "Discord verweigert die Aktion (fehlende Bot-Rechte)"}, status=502
            )
        except discord.HTTPException as exc:
            return web.json_response({"error": f"Discord-Fehler: {exc}"}, status=502)
        return web.json_response({"ok": True})

    async def remove_participant_role(request):
        """Teilnehmer-Rolle entziehen (idempotent — remove ohne Rolle ist ok)."""
        role, member, error = await _resolve_role_member(request)
        if error is not None:
            return error
        try:
            await member.remove_roles(role, reason="Turnier-Automatisierung: Abmeldung")
        except discord.NotFound:
            return web.json_response(
                {"error": "Rolle oder Member wurde zwischenzeitlich entfernt"}, status=404
            )
        except discord.Forbidden:
            return web.json_response(
                {"error": "Discord verweigert die Aktion (fehlende Bot-Rechte)"}, status=502
            )
        except discord.HTTPException as exc:
            return web.json_response({"error": f"Discord-Fehler: {exc}"}, status=502)
        return web.json_response({"ok": True})

    app = web.Application()
    app.router.add_get("/internal/members/{discord_id}/roles", member_roles)
    app.router.add_post("/internal/tournaments/discord", create_tournament_discord)
    app.router.add_delete("/internal/tournaments/discord", delete_tournament_discord)
    app.router.add_post(
        "/internal/tournaments/discord/role-assign", assign_participant_role
    )
    app.router.add_post(
        "/internal/tournaments/discord/role-remove", remove_participant_role
    )
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
