"""Turnier-Slash-Commands für Teilnehmer (jeder darf sie nutzen).

  /turnier-hilfe   — rollenabhängige Übersicht aller Turnier-Befehle
  /turniere        — Liste offener/kommender Turniere (Embed + Links)
  /turnier-info    — Status, Teams, Link zu einem Turnier
  /anmelden        — Gating-Hinweis + personalisierter Deeplink zur Turnierseite
  /mein-team       — eigene Teams/Turniere + Deeplink /team/:id
"""
import discord

from . import turnier_common as tc


# ------------------------------------------------------------------ /turnier-hilfe

def build_help_text(cfg_json, member):
    """Baut die rollenabhängige Hilfe. Teilnehmer-Block immer, EM/Admin- und
    Caster-Blöcke nur, wenn der Member die jeweilige Rolle trägt. Reine
    Stringfunktion → direkt testbar."""
    lines = ["**Turnier-Befehle**", "", "__Für alle Teilnehmer__"]
    lines += [
        "`/turnier-hilfe` — diese Übersicht",
        "`/turniere` — offene & kommende Turniere",
        "`/turnier-info <name>` — Status, Teams, Link",
        "`/anmelden <turnier>` — Anmeldung (öffnet deine persönliche Turnierseite)",
        "`/mein-team` — deine Teams & Turniere",
    ]
    if tc.is_em_or_admin(cfg_json, member):
        lines += [
            "",
            "__Eventmanagement / Admin__",
            "`/turnier-erstellen` — neues Turnier (Admin-Bereich)",
            "`/anmeldung-oeffnen <t>` — Anmeldung freigeben",
            "`/turnier-starten <t>` — Turnier starten",
            "`/ko-starten <t>` — KO-Phase aus den Gruppen starten",
            "`/turnier-beenden <t>` — Turnier beenden (irreversibel)",
        ]
    if tc.is_caster(cfg_json, member):
        lines += [
            "",
            "__Caster__",
            "`/caster-info <turnier>` — Caster-Seite (folgt mit M6)",
        ]
    return "\n".join(lines)


async def hilfe_handler(cfg_json, interaction):
    await interaction.response.defer(ephemeral=True)
    await interaction.edit_original_response(content=build_help_text(cfg_json, interaction.user))


# ------------------------------------------------------------------ /turniere

async def turniere_handler(cfg_json, interaction):
    await interaction.response.defer(ephemeral=True)
    base_url = tc.get_base_url(cfg_json)
    token = tc.get_service_token(cfg_json)
    if not token:
        await interaction.edit_original_response(content=tc.UNAVAILABLE_MSG)
        return
    try:
        tournaments = await tc.fetch_tournaments(base_url, token)
    except tc.BACKEND_ERRORS:
        await interaction.edit_original_response(content=tc.UNAVAILABLE_MSG)
        return

    if not tournaments:
        await interaction.edit_original_response(
            content="Aktuell sind keine offenen oder kommenden Turniere ausgeschrieben."
        )
        return

    embed = discord.Embed(
        title="Offene & kommende Turniere", color=discord.Color.blurple()
    )
    for t in tournaments[:25]:  # Discord-Limit: 25 Felder
        url = tc.public_tournament_url(cfg_json, t["slug"])
        embed.add_field(
            name=t["name"],
            value=(
                f"Status: **{tc.status_label(t['status'])}** · "
                f"Teams: {t['team_count']}/{t['max_teams']}\n[Zur Turnierseite]({url})"
            ),
            inline=False,
        )
    await interaction.edit_original_response(embed=embed)


# ------------------------------------------------------------------ /turnier-info

async def info_handler(cfg_json, interaction, name_oder_slug):
    await interaction.response.defer(ephemeral=True)
    base_url = tc.get_base_url(cfg_json)
    token = tc.get_service_token(cfg_json)
    if not token:
        await interaction.edit_original_response(content=tc.UNAVAILABLE_MSG)
        return
    try:
        t = await tc.fetch_tournament(base_url, token, name_oder_slug)
    except tc.BACKEND_ERRORS:
        await interaction.edit_original_response(content=tc.UNAVAILABLE_MSG)
        return
    if not t:
        await interaction.edit_original_response(content=tc.NOT_FOUND_MSG)
        return

    url = tc.public_tournament_url(cfg_json, t["slug"])
    embed = discord.Embed(title=t["name"], url=url, color=discord.Color.blurple())
    embed.add_field(name="Status", value=tc.status_label(t["status"]), inline=True)
    embed.add_field(
        name="Teams", value=f"{t['team_count']}/{t['max_teams']}", inline=True
    )
    embed.add_field(name="Turnierseite", value=url, inline=False)
    await interaction.edit_original_response(embed=embed)


# ------------------------------------------------------------------ /anmelden

async def anmelden_handler(cfg_json, interaction, turnier):
    await interaction.response.defer(ephemeral=True)
    base_url = tc.get_base_url(cfg_json)
    token = tc.get_service_token(cfg_json)
    if not token:
        await interaction.edit_original_response(content=tc.UNAVAILABLE_MSG)
        return
    try:
        t = await tc.fetch_tournament(base_url, token, turnier)
    except tc.BACKEND_ERRORS:
        await interaction.edit_original_response(content=tc.UNAVAILABLE_MSG)
        return
    if not t:
        await interaction.edit_original_response(content=tc.NOT_FOUND_MSG)
        return

    # Personalisierter Login-Deeplink mit Ziel = Turnierseite. Die eigentliche
    # Anmeldung (Team/Solo, Gating-Prüfung) passiert auf der Website.
    try:
        url = await tc.request_deeplink(
            base_url, token, interaction.user.id, interaction.user.name,
            redirect_path=f"/t/{t['slug']}",
        )
    except tc.BACKEND_ERRORS:
        await interaction.edit_original_response(content=tc.UNAVAILABLE_MSG)
        return
    if not url:
        await interaction.edit_original_response(content=tc.UNAVAILABLE_MSG)
        return

    await interaction.edit_original_response(
        content=(
            f"**Anmeldung zu „{t['name']}“**\n"
            "Zum Mitspielen müssen **Discord** und **Twitch** verknüpft sein "
            "(bei strenger Smurf-Prüfung zusätzlich **Riot**). Das prüft die "
            "Website beim Anmelden.\n\n"
            f"Dein persönlicher Link zur Turnierseite:\n{url}\n"
            "-# 15 Minuten gültig, nur einmal verwendbar. Teile ihn mit niemandem."
        )
    )


# ------------------------------------------------------------------ /mein-team

async def mein_team_handler(cfg_json, interaction):
    await interaction.response.defer(ephemeral=True)
    base_url = tc.get_base_url(cfg_json)
    token = tc.get_service_token(cfg_json)
    if not token:
        await interaction.edit_original_response(content=tc.UNAVAILABLE_MSG)
        return
    try:
        teams = await tc.fetch_my_teams(base_url, token, interaction.user.id)
    except tc.BACKEND_ERRORS:
        await interaction.edit_original_response(content=tc.UNAVAILABLE_MSG)
        return

    if not teams:
        await interaction.edit_original_response(
            content=(
                "Du bist in keinem Turnier-Team eingetragen.\n"
                "Mit `/turniere` findest du offene Turniere, mit `/anmelden` meldest du dich an."
            )
        )
        return

    embed = discord.Embed(title="Deine Teams & Turniere", color=discord.Color.green())
    for t in teams[:25]:
        deeplink = tc.public_tournament_url(cfg_json, t["tournament_slug"])
        leader = " · 👑 Leader" if t.get("is_leader") else ""
        embed.add_field(
            name=f"{t['team_name']} — {t['tournament_name']}",
            value=(
                f"Status: **{tc.status_label(t['status'])}**{leader}\n"
                f"[Zum Turnier]({deeplink})"
            ),
            inline=False,
        )
    # Persönlicher Deeplink zur eigenen Team-Seite (Login-Token) — bei genau
    # einem Team direkt auf /team/:id, sonst aufs Profil.
    redirect = f"/team/{teams[0]['team_id']}" if len(teams) == 1 else "/profil"
    try:
        url = await tc.request_deeplink(
            base_url, token, interaction.user.id, interaction.user.name,
            redirect_path=redirect,
        )
    except tc.BACKEND_ERRORS:
        url = None
    if url:
        embed.add_field(
            name="Team verwalten",
            value=f"[Persönlicher Login-Link]({url}) (15 Min, einmalig)",
            inline=False,
        )
    await interaction.edit_original_response(embed=embed)
