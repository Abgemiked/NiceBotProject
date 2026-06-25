import discord

import audit_log


def _as_id_set(value):
    """Normalisiert ALLOWED_ROLE_IDS zu einem set[int] — akzeptiert eine Liste
    (neu) ebenso wie eine einzelne ID (abwärtskompatibel zur alten Config)."""
    if value is None:
        return set()
    if not isinstance(value, (list, tuple, set)):
        value = [value]
    out = set()
    for v in value:
        try:
            out.add(int(v))
        except (TypeError, ValueError):
            continue
    return out


async def handle_message_delete(payload, bot, LOG_CHANNEL_ID, MUSIC_CHANNEL_ID, ALLOWED_ROLE_ID):
    channel = bot.get_channel(payload.channel_id)
    if channel is None:
        return
    message = payload.cached_message
    if message is None or message.author.bot:
        return
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel is None:
        return
    allowed_role_ids = _as_id_set(ALLOWED_ROLE_ID)
    allowed_role_found = False
    for role in message.author.roles:
        if role.id in allowed_role_ids:
            if channel.id == MUSIC_CHANNEL_ID:
                return
            allowed_role_found = True
            await log_channel.send(f'Eine **Teamnachricht** wurde aus dem Channel **{message.channel.name}** gelöscht.')
            break
    if not allowed_role_found:
        await log_channel.send(f'Die Nachricht "**{message.content}**" von **{message.author.name}** wurde aus dem Channel **{message.channel.name}** gelöscht.')

    # Persistentes Audit-Log (best effort; bricht den Bot bei Fehler nicht).
    audit_log.log_event(
        "message_delete",
        target_id=message.author.id,
        target_name=message.author.name,
        channel_id=channel.id,
        content=message.content,
        meta={"team_message": allowed_role_found, "channel_name": message.channel.name},
    )


async def on_raw_message_delete_handler(payload, bot, LOG_CHANNEL_ID, MUSIC_CHANNEL_ID, ALLOWED_ROLE_ID):
    await handle_message_delete(payload, bot, LOG_CHANNEL_ID, MUSIC_CHANNEL_ID, ALLOWED_ROLE_ID)
