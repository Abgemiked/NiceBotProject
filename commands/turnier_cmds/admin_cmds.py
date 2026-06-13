"""Rollen-gated Turnier-Slash-Commands (EM/Admin) + Caster.

Prinzip: KEINE schreibenden Aktionen im Bot. Jeder Befehl prüft die
Discord-Rolle des Aufrufers und liefert dann einen personalisierten Deeplink
zur Verwaltung/Bestätigung auf der Website (eine Quelle der Wahrheit).
Begründung Deeplink statt Inline-Service-Token-Aktion: sicherer (die Website
kennt den vollen Lifecycle/Start-Gate, der Bot müsste ihn duplizieren) und
auditierbar (Aktion läuft unter der echten Session des EM).
"""
from . import turnier_common as tc

FORBIDDEN_EM = "Dieser Befehl ist dem Eventmanagement / Admin vorbehalten."
FORBIDDEN_CASTER = "Dieser Befehl ist Castern vorbehalten."


async def _deeplink_or_error(cfg_json, interaction, redirect_path):
    """Holt einen Deeplink (Login-Token). Liefert URL oder None (Fehler ist
    dann bereits an den Nutzer gemeldet)."""
    base_url = tc.get_base_url(cfg_json)
    token = tc.get_service_token(cfg_json)
    if not token:
        await interaction.edit_original_response(content=tc.UNAVAILABLE_MSG)
        return None
    try:
        url = await tc.request_deeplink(
            base_url, token, interaction.user.id, interaction.user.name,
            redirect_path=redirect_path,
        )
    except tc.BACKEND_ERRORS:
        await interaction.edit_original_response(content=tc.UNAVAILABLE_MSG)
        return None
    if not url:
        await interaction.edit_original_response(content=tc.UNAVAILABLE_MSG)
        return None
    return url


async def _resolve_tournament(cfg_json, interaction, turnier):
    """Sucht ein Turnier per name/slug. Liefert dict oder None (Fehler gemeldet)."""
    base_url = tc.get_base_url(cfg_json)
    token = tc.get_service_token(cfg_json)
    if not token:
        await interaction.edit_original_response(content=tc.UNAVAILABLE_MSG)
        return None
    try:
        t = await tc.fetch_tournament(base_url, token, turnier)
    except tc.BACKEND_ERRORS:
        await interaction.edit_original_response(content=tc.UNAVAILABLE_MSG)
        return None
    if not t:
        await interaction.edit_original_response(content=tc.NOT_FOUND_MSG)
        return None
    return t


# ------------------------------------------------------------------ /turnier-erstellen

async def erstellen_handler(cfg_json, interaction):
    await interaction.response.defer(ephemeral=True)
    if not tc.is_em_or_admin(cfg_json, interaction.user):
        await interaction.edit_original_response(content=FORBIDDEN_EM)
        return
    url = await _deeplink_or_error(cfg_json, interaction, "/turniere")
    if not url:
        return
    await interaction.edit_original_response(
        content=(
            "**Neues Turnier anlegen**\n"
            f"Im Verwaltungsbereich anlegen:\n{url}\n"
            "-# 15 Minuten gültig, nur einmal verwendbar."
        )
    )


# --------------------------- gemeinsamer Lifecycle-Deeplink (öffnen/starten/ko)

async def _lifecycle_deeplink(cfg_json, interaction, turnier, titel, hinweis):
    await interaction.response.defer(ephemeral=True)
    if not tc.is_em_or_admin(cfg_json, interaction.user):
        await interaction.edit_original_response(content=FORBIDDEN_EM)
        return
    t = await _resolve_tournament(cfg_json, interaction, turnier)
    if not t:
        return
    url = await _deeplink_or_error(cfg_json, interaction, f"/t/{t['slug']}")
    if not url:
        return
    extra = f"\n{hinweis}" if hinweis else ""
    await interaction.edit_original_response(
        content=(
            f"**{titel}: „{t['name']}“**{extra}\n"
            f"Aktion auf der Turnierseite bestätigen:\n{url}\n"
            "-# 15 Minuten gültig, nur einmal verwendbar."
        )
    )


async def anmeldung_oeffnen_handler(cfg_json, interaction, turnier):
    await _lifecycle_deeplink(
        cfg_json, interaction, turnier, "Anmeldung öffnen", None
    )


async def turnier_starten_handler(cfg_json, interaction, turnier):
    await _lifecycle_deeplink(
        cfg_json, interaction, turnier, "Turnier starten",
        "Start nur möglich, wenn das Start-Gate erfüllt ist (Teams + Spielzeiten).",
    )


async def ko_starten_handler(cfg_json, interaction, turnier):
    await _lifecycle_deeplink(
        cfg_json, interaction, turnier, "KO-Phase starten",
        "Nur im Gruppen→KO-Modus, wenn alle Gruppen-Matches entschieden sind.",
    )


async def turnier_beenden_handler(cfg_json, interaction, turnier):
    await _lifecycle_deeplink(
        cfg_json, interaction, turnier, "Turnier beenden",
        "⚠️ **Irreversibel** — beendet das Turnier endgültig. Bitte sorgfältig prüfen.",
    )


# ------------------------------------------------------------------ /caster-info

async def caster_info_handler(cfg_json, interaction, turnier):
    await interaction.response.defer(ephemeral=True)
    if not tc.is_caster(cfg_json, interaction.user):
        await interaction.edit_original_response(content=FORBIDDEN_CASTER)
        return
    t = await _resolve_tournament(cfg_json, interaction, turnier)
    if not t:
        return
    # Caster-Seite kommt mit M6 — bis dahin Info + Link zur öffentlichen Seite.
    url = tc.public_tournament_url(cfg_json, t["slug"])
    await interaction.edit_original_response(
        content=(
            f"**Caster-Info: „{t['name']}“**\n"
            "Die dedizierte Caster-Seite (Overlays, Match-Details) folgt mit **M6**.\n"
            f"Bis dahin: öffentliche Turnierseite → {url}"
        )
    )
