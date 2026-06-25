import discord

import audit_log


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
    allowed_role_found = False
    for role in message.author.roles:
        if role.id == ALLOWED_ROLE_ID:
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
