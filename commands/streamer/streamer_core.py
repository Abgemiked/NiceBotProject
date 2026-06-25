"""Gemeinsame Streamer-Logik (Kategorie + Channels + Rollen).

Genutzt sowohl vom Slash-Command (/streamer, /streamer_löschen) als auch vom
Web-Verwaltungstool über die Service-API. Reine Discord-Operationen auf einer
übergebenen Guild — keine Interaction-Kopplung.
"""
import discord

CATEGORY_PREFIX = "📺 "


def _names(streamer_name):
    s = streamer_name.capitalize()
    return {
        "display": s,
        "category": f"{CATEGORY_PREFIX}{s}",
        "text": ["🔊-streaming", "🎥-clips"],
        "voice": [f"💻 {s}-Live", f"💻 {s}-Warteraum"],
        "roles": [f"👨‍💻 {s}", f"👨‍💻 {s}-Mod", f"👨‍💻 {s}-Zuschauer"],
    }


def _perms(full):
    """Berechtigungs-Set: full=True für Streamer-Rolle, sonst Mod/Zuschauer-nah."""
    return discord.PermissionOverwrite(
        view_channel=True, manage_channels=full, manage_permissions=full,
        manage_webhooks=full, create_instant_invite=True, send_messages=True,
        send_messages_in_threads=True, create_public_threads=True,
        create_private_threads=True, embed_links=True, attach_files=True,
        add_reactions=True, use_external_emojis=True, use_external_stickers=True,
        mention_everyone=False, manage_messages=full, manage_threads=full,
        read_message_history=True, send_tts_messages=True,
        use_application_commands=True, send_voice_messages=True, connect=True,
        speak=True, stream=True, use_embedded_activities=True, use_soundboard=True,
        use_external_sounds=True, use_voice_activation=True, mute_members=full,
        deafen_members=full, move_members=full, request_to_speak=True,
        manage_events=full,
    )


def streamer_exists(guild, streamer_name):
    n = _names(streamer_name)
    return discord.utils.get(guild.categories, name=n["category"]) is not None


def list_streamers(guild):
    """Findet bestehende Streamer anhand der Kategorie-Präfixe."""
    out = []
    for cat in guild.categories:
        if cat.name.startswith(CATEGORY_PREFIX):
            out.append({
                "name": cat.name[len(CATEGORY_PREFIX):],
                "category_id": str(cat.id),
                "channels": len(cat.channels),
            })
    return out


async def create_streamer(guild, streamer_name):
    """Legt Kategorie + Channels + Rollen für einen Streamer an (idempotenz-arm:
    der Aufrufer prüft via streamer_exists vorab)."""
    n = _names(streamer_name)
    category = await guild.create_category(n["category"])
    for name in n["text"]:
        await category.create_text_channel(name)
    for name in n["voice"]:
        await category.create_voice_channel(name)

    roles = []
    for name in n["roles"]:
        roles.append(await guild.create_role(name=name))
    for role in roles:
        full = role.name == n["roles"][0]  # nur die Streamer-Rolle bekommt volle Rechte
        await category.set_permissions(role, overwrite=_perms(full))
    await category.set_permissions(guild.default_role, read_messages=False, connect=False)
    for channel in category.channels:
        await channel.edit(sync_permissions=True)
    return n["display"]


async def delete_streamer(guild, streamer_name):
    """Löscht Kategorie + enthaltene Channels + die drei Rollen. False, wenn
    keine Kategorie existiert."""
    n = _names(streamer_name)
    category = discord.utils.get(guild.categories, name=n["category"])
    if category is None:
        return False
    for channel in list(category.channels):
        await channel.delete()
    for role_name in n["roles"]:
        role = discord.utils.get(guild.roles, name=role_name)
        if role:
            await role.delete()
    await category.delete()
    return True
