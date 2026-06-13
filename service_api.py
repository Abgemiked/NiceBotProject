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

Phase 7 Stage B — Team-Channels + Team-Rollen:

    Pro Team in einem Turnier ein Text- + Voice-Channel in der Turnier-
    Kategorie, sichtbar/schreibbar NUR für Teammitglieder (Leader/Member-
    Rolle) + EM (Vollrechte) + Bot; @everyone unsichtbar (kein Leak).
    Pro TEAM zwei wiederverwendbare Rollen "[Teamname]-Leader"/"-Member"
    (Teamnamen sind global eindeutig, Team nimmt an mehreren Turnieren teil).

    POST /internal/teams/discord
        Body: {tournament_category_id, team_name, member_discord_ids[],
               leader_discord_id, existing_leader_role_id?,
               existing_member_role_id?}
        Rollen wiederverwenden (existing_*) ODER anlegen; Text+Voice-Channel
        in der Kategorie; Rollen an Leader/Member vergeben.
        201 → {text_channel_id, voice_channel_id, leader_role_id, member_role_id}
        502 → {error, created}  (Teilzustand für Backend-Cleanup)

    DELETE /internal/teams/discord
        Body: {text_channel_id, voice_channel_id, leader_role_id?,
               member_role_id?, delete_roles: bool}
        Channels löschen (Guild-Scope, 404-tolerant). Rollen NUR wenn
        delete_roles=true (Backend entscheidet anhand Wiederverwendung).

    POST /internal/teams/discord/role-assign  {role_id, discord_id}
    POST /internal/teams/discord/role-remove  {role_id, discord_id}
        F1-Guard: akzeptieren NUR Rollen mit Suffix "-Leader"/"-Member".

Phase 7 Stage B.1 — globale, anpingbare Rolle "Teamleader":

    EINE serverweite Rolle "Teamleader" (mentionable=True, keine Permissions),
    NICHT pro Team/Turnier. EM darf sie in Turnier-Kategorie-Channeln pingen;
    das Notification-Scoping ergibt sich automatisch aus der Channel-
    Sichtbarkeit (nur turnierteilnehmer-[T]-Inhaber sehen die Channels) — keine
    Zusatzlogik. Der Bot selbst pingt nie.

    POST /internal/teamleader-role/assign  {discord_id}
    POST /internal/teamleader-role/remove  {discord_id}
        Rolle wird per ensure-create sichergestellt. Guard: es wird
        AUSSCHLIESSLICH die Rolle mit exakt dem Namen "Teamleader" angefasst
        (sonst 403; analog Stage-A.5/F1). 404-tolerant (Member weg).
        200 → {"ok": true, "role_id": "…"}

    Kategorie-Position: create_tournament_discord sortiert die neue Turnier-
    Kategorie ZWISCHEN "Öffentlich" und "Temporäre Channel" ein (Anker per Name
    zur Laufzeit, case-insensitive/umlaut-tolerant; Default-Position bleibt,
    wenn kein Anker gefunden wird — kein Fehler).

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

# Stage B: Team-Rollen (Team-Ebene, über mehrere Turniere wiederverwendet).
# Namens-Suffixe — Rolle heißt "[Teamname]-Leader" bzw. "[Teamname]-Member".
# Der Suffix dient als Defense-in-Depth-Guard (analog PARTICIPANT_ROLE_PREFIX,
# Audit F1): Team-Rollen-Endpoints akzeptieren nur Rollen mit diesem Suffix,
# damit ein geleakter Service-Token keine EM-/Mod-Rollen vergeben kann.
TEAM_ROLE_LEADER_SUFFIX = "-Leader"
TEAM_ROLE_MEMBER_SUFFIX = "-Member"
MAX_ROLE_NAME = 100
# Stage B: Team-Channels je (Team, Turnier)
TEAM_TEXT_CHANNEL_PREFIX = "team-"
TEAM_VOICE_CHANNEL_PREFIX = "Team "

# Stage B.1: EINE serverweite, anpingbare Rolle "Teamleader" (NICHT pro Team/
# Turnier). Wird vom Backend jedem aktiven Turnier-Teamleader vergeben/entzogen.
# Der exakte Name ist der Guard (analog Stage-A.5/F1): die Teamleader-Endpoints
# vergeben/entziehen NUR genau diese Rolle. mentionable=True (EM darf @Teamleader
# in Kategorie-Channeln pingen); der Bot selbst pingt nie.
TEAMLEADER_ROLE_NAME = "Teamleader"

# Anker-Kategorien für die Stage-B.1-Positionierung der Turnier-Kategorie.
# Zur Laufzeit per Name aufgelöst (case-insensitive, mit/ohne Umlaut), damit
# keine IDs fest verdrahtet werden. Turnier-Kategorie soll direkt UNTER
# "Öffentlich" (bzw. direkt ÜBER "Temporäre Channel") liegen.
PUBLIC_CATEGORY_NAMES = ("öffentlich", "offentlich")
TEMP_CATEGORY_NAMES = ("temporäre channel", "temporare channel")


def _team_role_names(team_name):
    """Liefert (leader_name, member_name) ≤100 Zeichen.

    Der Teamname wird so gekürzt, dass auch mit Suffix das Discord-Limit von
    100 Zeichen eingehalten wird (sonst wirft create_role).
    """
    leader_budget = MAX_ROLE_NAME - len(TEAM_ROLE_LEADER_SUFFIX)
    member_budget = MAX_ROLE_NAME - len(TEAM_ROLE_MEMBER_SUFFIX)
    base = min(leader_budget, member_budget)
    short = team_name.strip()[:base]
    return short + TEAM_ROLE_LEADER_SUFFIX, short + TEAM_ROLE_MEMBER_SUFFIX


def _is_team_role(role):
    """True, wenn der Rollenname auf ein Team-Rollen-Suffix endet (F1-Guard)."""
    return role.name.endswith(TEAM_ROLE_LEADER_SUFFIX) or role.name.endswith(
        TEAM_ROLE_MEMBER_SUFFIX
    )


async def _ensure_teamleader_role(guild, reason):
    """Die EINE serverweite Rolle "Teamleader" sicherstellen (ensure-create).

    Liefert (role, None) bei Erfolg oder (None, error_message). Sucht zunächst
    eine bestehende Rolle mit exakt diesem Namen; legt sie sonst an
    (mentionable=True, keine Permissions). Idempotent.
    """
    role = discord.utils.get(guild.roles, name=TEAMLEADER_ROLE_NAME)
    if role is not None:
        return role, None
    try:
        role = await guild.create_role(
            name=TEAMLEADER_ROLE_NAME,
            mentionable=True,
            hoist=False,
            permissions=discord.Permissions.none(),
            reason=reason,
        )
        return role, None
    except discord.Forbidden:
        return None, "Discord verweigert das Anlegen der Teamleader-Rolle (fehlende Bot-Rechte)"
    except discord.HTTPException as exc:
        return None, f"Discord-Fehler beim Anlegen der Teamleader-Rolle: {exc}"


def _resolve_anchor_categories(guild):
    """Anker-Kategorien "Öffentlich" und "Temporäre Channel" per Name auflösen.

    Case-insensitive, tolerant gegenüber fehlenden Umlauten. Liefert
    (public_category | None, temp_category | None). Wird zur Laufzeit
    ausgewertet — keine fest verdrahteten IDs.
    """
    public_cat = None
    temp_cat = None
    for cat in guild.categories:
        low = cat.name.strip().lower()
        if public_cat is None and low in PUBLIC_CATEGORY_NAMES:
            public_cat = cat
        elif temp_cat is None and low in TEMP_CATEGORY_NAMES:
            temp_cat = cat
    return public_cat, temp_cat


async def _position_tournament_category(guild, category):
    """Turnier-Kategorie ZWISCHEN "Öffentlich" und "Temporäre Channel" einsortieren.

    Idempotent/wiederholbar (auch aus einem späteren Sync nutzbar). Bevorzugt
    category.move(after=Öffentlich) — robust gegen Discord-Reorder-Eigenheiten;
    fällt auf move(before=Temporäre Channel) bzurück, wenn nur der untere Anker
    existiert. Ist KEIN Anker auffindbar, bleibt die Default-Position bestehen
    (kein Fehler — nur Logeintrag). Wirft nie.
    """
    try:
        public_cat, temp_cat = _resolve_anchor_categories(guild)
        if public_cat is None and temp_cat is None:
            print(
                "Turnier-Kategorie-Position: Anker 'Öffentlich'/'Temporäre Channel' "
                "nicht gefunden — Default-Position bleibt"
            )
            return False
        if public_cat is not None:
            await category.move(after=public_cat)
        else:
            await category.move(before=temp_cat)
        return True
    except (discord.Forbidden, discord.HTTPException) as exc:
        # Position ist nice-to-have; ein Fehler darf die Provisionierung nie
        # killen (die Kategorie ist bereits angelegt).
        print(f"Turnier-Kategorie-Position konnte nicht gesetzt werden: {exc}")
        return False
    except Exception as exc:  # noqa: BLE001 — defensiv, best effort
        print(f"Turnier-Kategorie-Position unerwarteter Fehler: {exc}")
        return False


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

            # Stage B.1: Kategorie ZWISCHEN "Öffentlich" und "Temporäre Channel"
            # einsortieren (best effort; Default-Position bleibt, wenn die Anker
            # fehlen). NACH dem Anlegen — die Kategorie existiert bereits.
            await _position_tournament_category(guild, category)

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

    async def _resolve_role_member(request, role_guard=None, guard_error=None):
        """Gemeinsame Validierung für role-assign/role-remove.

        Liefert (role, member, None) oder (None, None, Fehler-Response).
        404-tolerant: Rolle/Member nicht (mehr) vorhanden → klare Meldung,
        kein Crash — das Backend behandelt Rollen-Sync als best effort.

        role_guard: Callable(role)->bool. Default = Teilnehmer-Rolle (Stage
        A.5). Stage B übergibt _is_team_role. Schlägt der Guard fehl → 403
        mit guard_error (Defense-in-Depth gegen Token-Leck, Audit F1).
        """
        if role_guard is None:
            role_guard = lambda r: r.name.startswith(PARTICIPANT_ROLE_PREFIX)
            guard_error = (
                "Rolle {role_id} ist keine Turnier-Teilnehmer-Rolle "
                f"(Name muss mit '{PARTICIPANT_ROLE_PREFIX}' beginnen) "
                "— Zuweisung/Entzug verweigert"
            )
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

        # Defense-in-Depth (Audit A.5/F1): NUR die per role_guard erlaubten
        # Rollen sind über diese Endpoints verwaltbar. Ohne diesen Guard könnte
        # ein geleakter Service-Token jedem Member jede Rolle (EM/Mod/…) geben.
        if not role_guard(role):
            return None, None, web.json_response(
                {"error": guard_error.format(role_id=role_id)},
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

    # --- Stage B: Team-Channels + Team-Rollen (pro Team in einem Turnier) ---

    async def create_team_discord(request):
        """Team-Rollen (wiederverwendbar) + Text/Voice-Channel je (Team,Turnier).

        Body: {tournament_category_id, team_name, member_discord_ids[],
               leader_discord_id, existing_leader_role_id?, existing_member_role_id?}

        Rollen: existieren existing_*_role_id → wiederverwenden (Team nimmt an
        weiterem Turnier teil), sonst "[team]-Leader"/"[team]-Member" anlegen.
        Channels: Text + Voice in der Turnier-Kategorie, NUR für Leader/Member-
        Rolle (+ EM + Bot) sichtbar; @everyone unsichtbar (kein Leak).
        Antwort: text_channel_id, voice_channel_id, leader_role_id, member_role_id.
        Teilzustand wird bei Fehlern in "created" zurückgegeben (kein stiller
        Orphan — das Backend speichert/räumt ab).
        """
        if not _token_ok(request, cfg_json.get("TURNIER_SERVICE_TOKEN")):
            return web.json_response({"error": "Ungültiger Service-Token"}, status=401)

        try:
            body = await request.json()
        except Exception:
            return web.json_response({"error": "Ungültiger JSON-Body"}, status=400)
        if not isinstance(body, dict):
            return web.json_response({"error": "Ungültiger JSON-Body"}, status=400)

        category_id = body.get("tournament_category_id")
        team_name = body.get("team_name")
        leader_discord_id = body.get("leader_discord_id")
        member_discord_ids = body.get("member_discord_ids") or []
        existing_leader = body.get("existing_leader_role_id")
        existing_member = body.get("existing_member_role_id")

        if not _valid_snowflake(category_id):
            return web.json_response(
                {"error": "tournament_category_id muss eine gültige Discord-ID sein"},
                status=400,
            )
        if not isinstance(team_name, str) or not team_name.strip():
            return web.json_response({"error": "team_name ist Pflicht"}, status=400)
        if not isinstance(member_discord_ids, list):
            return web.json_response(
                {"error": "member_discord_ids muss eine Liste sein"}, status=400
            )
        for value in [leader_discord_id, existing_leader, existing_member, *member_discord_ids]:
            if value is not None and not _valid_snowflake(value):
                return web.json_response(
                    {"error": f"Ungültige Discord-ID: {value!r}"}, status=400
                )

        guild = bot.get_guild(cfg_json.get("GUILD_ID"))
        if guild is None:
            return web.json_response({"error": "Guild nicht verfügbar"}, status=503)

        category = guild.get_channel(int(category_id))
        if category is None or not isinstance(category, discord.CategoryChannel):
            return web.json_response(
                {"error": f"Kategorie {category_id} nicht (mehr) vorhanden"}, status=404
            )

        em_role_id = int(cfg_json.get("TURNIER_EM_ROLE_ID") or DEFAULT_EM_ROLE_ID)
        em_role = guild.get_role(em_role_id)
        if em_role is None:
            return web.json_response(
                {"error": f"EM-Rolle {em_role_id} nicht auf der Guild gefunden"},
                status=503,
            )

        leader_name, member_name = _team_role_names(team_name)
        created = {}

        try:
            # Rollen: wiederverwenden (Team in 2.+ Turnier) ODER neu anlegen.
            leader_role = (
                guild.get_role(int(existing_leader)) if existing_leader else None
            )
            member_role = (
                guild.get_role(int(existing_member)) if existing_member else None
            )
            if leader_role is None:
                leader_role = await guild.create_role(
                    name=leader_name, mentionable=False, hoist=False,
                    reason=f"Turnier-Automatisierung: Team-Leader-Rolle {team_name}",
                )
            if member_role is None:
                member_role = await guild.create_role(
                    name=member_name, mentionable=False, hoist=False,
                    reason=f"Turnier-Automatisierung: Team-Member-Rolle {team_name}",
                )
            created["leader_role_id"] = str(leader_role.id)
            created["member_role_id"] = str(member_role.id)

            full = _full_access_overwrite()
            visible = discord.PermissionOverwrite(
                view_channel=True, send_messages=True, connect=True, speak=True,
                read_message_history=True,
            )
            # @everyone unsichtbar — kein Leak; nur Leader/Member-Rolle + EM + Bot.
            overwrites = {
                em_role: full,
                guild.me: full,
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                leader_role: visible,
                member_role: visible,
            }

            text_name = (TEAM_TEXT_CHANNEL_PREFIX + team_name.strip())[:MAX_CHANNEL_NAME]
            text = await guild.create_text_channel(
                text_name, category=category, overwrites=overwrites,
                reason=f"Turnier-Automatisierung: Team-Textchannel {team_name}",
            )
            created["text_channel_id"] = str(text.id)

            voice_name = (TEAM_VOICE_CHANNEL_PREFIX + team_name.strip())[:MAX_CHANNEL_NAME]
            voice = await guild.create_voice_channel(
                voice_name, category=category, overwrites=overwrites,
                reason=f"Turnier-Automatisierung: Team-Voicechannel {team_name}",
            )
            created["voice_channel_id"] = str(voice.id)

            # Rollen an aktuelle Mitglieder vergeben (best effort je Member —
            # ein fehlendes Guild-Mitglied darf die Provisionierung nicht killen).
            async def _grant(discord_id, role):
                m = guild.get_member(int(discord_id))
                if m is None:
                    try:
                        m = await guild.fetch_member(int(discord_id))
                    except discord.HTTPException:
                        return
                try:
                    await m.add_roles(role, reason="Turnier-Automatisierung: Team-Rolle")
                except discord.HTTPException:
                    pass

            if leader_discord_id:
                await _grant(leader_discord_id, leader_role)
            for mid in member_discord_ids:
                await _grant(mid, member_role)
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

    async def delete_team_discord(request):
        """Team-Channels löschen; Team-Rollen NUR wenn delete_roles=true.

        Body: {text_channel_id, voice_channel_id, leader_role_id?,
               member_role_id?, delete_roles: bool}
        Löscht AUSSCHLIESSLICH die übergebenen IDs (Guild-Scope, 404-tolerant).
        Rollen werden nur gelöscht, wenn delete_roles=true — das Backend
        entscheidet anhand der Wiederverwendung (Teamname noch in einem
        nicht-abgeschlossenen Turnier aktiv → Rollen behalten).
        """
        if not _token_ok(request, cfg_json.get("TURNIER_SERVICE_TOKEN")):
            return web.json_response({"error": "Ungültiger Service-Token"}, status=401)

        try:
            body = await request.json()
        except Exception:
            return web.json_response({"error": "Ungültiger JSON-Body"}, status=400)
        if not isinstance(body, dict):
            return web.json_response({"error": "Ungültiger JSON-Body"}, status=400)

        text_channel_id = body.get("text_channel_id")
        voice_channel_id = body.get("voice_channel_id")
        leader_role_id = body.get("leader_role_id")
        member_role_id = body.get("member_role_id")
        delete_roles = bool(body.get("delete_roles"))
        for value in [text_channel_id, voice_channel_id, leader_role_id, member_role_id]:
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
            if getattr(channel, "guild", None) is None or channel.guild.id != guild.id:
                errors.append(f"{label} {snowflake}: gehört nicht zur NiceCom-Guild")
                return
            try:
                await channel.delete(reason="Turnier-Automatisierung: Team-Cleanup")
                deleted.append(snowflake)
            except discord.NotFound:
                missing.append(snowflake)
            except discord.Forbidden:
                errors.append(f"{label} {snowflake}: fehlende Rechte")
            except discord.HTTPException as exc:
                errors.append(f"{label} {snowflake}: {exc}")

        async def delete_role_scoped(snowflake):
            # guild.get_role ist per Konstruktion auf DIESE Guild beschränkt.
            role = guild.get_role(int(snowflake))
            if role is None:
                missing.append(snowflake)
                return
            try:
                await role.delete(reason="Turnier-Automatisierung: Team-Cleanup")
                deleted.append(snowflake)
            except discord.NotFound:
                missing.append(snowflake)
            except discord.Forbidden:
                errors.append(f"Rolle {snowflake}: fehlende Rechte")
            except discord.HTTPException as exc:
                errors.append(f"Rolle {snowflake}: {exc}")

        if text_channel_id:
            await delete_channel_like(text_channel_id, "Team-Textchannel")
        if voice_channel_id:
            await delete_channel_like(voice_channel_id, "Team-Voicechannel")
        if delete_roles:
            if leader_role_id:
                await delete_role_scoped(leader_role_id)
            if member_role_id:
                await delete_role_scoped(member_role_id)

        payload = {"deleted": deleted, "missing": missing}
        if errors:
            payload["errors"] = errors
            return web.json_response(payload, status=502)
        return web.json_response(payload)

    # --- Stage B: Team-Rollen-Zuweisung (Mitglied-Add/Remove im Team) -------

    _TEAM_GUARD_ERROR = (
        "Rolle {role_id} ist keine Team-Rolle "
        f"(Name muss auf '{TEAM_ROLE_LEADER_SUFFIX}' oder "
        f"'{TEAM_ROLE_MEMBER_SUFFIX}' enden) — Zuweisung/Entzug verweigert"
    )

    async def assign_team_role(request):
        """Team-Rolle vergeben (idempotent — add_roles doppelt ist ok)."""
        role, member, error = await _resolve_role_member(
            request, role_guard=_is_team_role, guard_error=_TEAM_GUARD_ERROR
        )
        if error is not None:
            return error
        try:
            await member.add_roles(role, reason="Turnier-Automatisierung: Team-Rolle")
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

    async def remove_team_role(request):
        """Team-Rolle entziehen (idempotent — remove ohne Rolle ist ok)."""
        role, member, error = await _resolve_role_member(
            request, role_guard=_is_team_role, guard_error=_TEAM_GUARD_ERROR
        )
        if error is not None:
            return error
        try:
            await member.remove_roles(role, reason="Turnier-Automatisierung: Team-Austritt")
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

    # --- Stage B.1: globale, anpingbare Rolle "Teamleader" -------------------

    async def _resolve_teamleader_member(request):
        """Token + discord_id validieren, Member holen, Teamleader-Rolle sichern.

        Liefert (role, member, None) oder (None, None, Fehler-Response).
        Guard: es wird AUSSCHLIESSLICH die Rolle mit exakt dem Namen
        "Teamleader" angefasst (ensure-create) — ein geleakter Service-Token
        kann über diese Endpoints keine andere Rolle vergeben/entziehen.
        404-tolerant (Member weg → klare Meldung).
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
        discord_id = body.get("discord_id")
        if not _valid_snowflake(discord_id):
            return None, None, web.json_response(
                {"error": "discord_id muss eine gültige Discord-ID sein"}, status=400
            )

        guild = bot.get_guild(cfg_json.get("GUILD_ID"))
        if guild is None:
            return None, None, web.json_response(
                {"error": "Guild nicht verfügbar"}, status=503
            )

        # ensure-create: die EINE serverweite Teamleader-Rolle.
        role, err = await _ensure_teamleader_role(
            guild, reason="Turnier-Automatisierung: globale Teamleader-Rolle"
        )
        if role is None:
            return None, None, web.json_response({"error": err}, status=502)

        # Defense-in-Depth: NUR die Rolle mit exakt diesem Namen ist erlaubt.
        if role.name != TEAMLEADER_ROLE_NAME:
            return None, None, web.json_response(
                {"error": "Rolle ist nicht die Teamleader-Rolle — verweigert"},
                status=403,
            )
        # Rolle auf/über der Bot-Top-Rolle ist nicht verwaltbar → klare 403.
        if guild.me is not None and role >= guild.me.top_role:
            return None, None, web.json_response(
                {"error": "Teamleader-Rolle liegt auf/über der Bot-Rolle "
                          "und kann nicht verwaltet werden"},
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

    async def assign_teamleader_role(request):
        """Globale Teamleader-Rolle vergeben (idempotent)."""
        role, member, error = await _resolve_teamleader_member(request)
        if error is not None:
            return error
        try:
            await member.add_roles(role, reason="Turnier-Automatisierung: Teamleader")
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
        return web.json_response({"ok": True, "role_id": str(role.id)})

    async def remove_teamleader_role(request):
        """Globale Teamleader-Rolle entziehen (idempotent)."""
        role, member, error = await _resolve_teamleader_member(request)
        if error is not None:
            return error
        try:
            await member.remove_roles(role, reason="Turnier-Automatisierung: Teamleader entzogen")
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
        return web.json_response({"ok": True, "role_id": str(role.id)})

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
    # Stage B: Team-Channels + Team-Rollen
    app.router.add_post("/internal/teams/discord", create_team_discord)
    app.router.add_delete("/internal/teams/discord", delete_team_discord)
    app.router.add_post("/internal/teams/discord/role-assign", assign_team_role)
    app.router.add_post("/internal/teams/discord/role-remove", remove_team_role)
    # Stage B.1: globale Teamleader-Rolle (ensure-create, Body nur {discord_id})
    app.router.add_post(
        "/internal/teamleader-role/assign", assign_teamleader_role
    )
    app.router.add_post(
        "/internal/teamleader-role/remove", remove_teamleader_role
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
