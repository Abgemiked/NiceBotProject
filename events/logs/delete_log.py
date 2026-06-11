import discord
async def handle_message_delete(payload, bot, LOG_CHANNEL_ID, MUSIC_CHANNEL_ID, ALLOWED_ROLE_ID):
    channel = bot.get_channel(payload.channel_id)
    if channel is None:
        return
    message = payload.cached_message
    if message is None or message.author.bot:
        return
    allowed_role_found = False
    for role in message.author.roles:
        if role.id == ALLOWED_ROLE_ID:
            if channel.id == MUSIC_CHANNEL_ID:
                return
            else:
                allowed_role_found = True
                log_channel = bot.get_channel(int(LOG_CHANNEL_ID))
                await log_channel.send(f'Eine **Teamnachricht** wurde aus dem Channel **{message.channel.name}** gelöscht.')
                break
    if not allowed_role_found:
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        await log_channel.send(f'Die Nachricht "**{message.content}**" von **{message.author.name}** wurde aus dem Channel **{message.channel.name}** gelöscht.')


async def on_raw_message_delete_handler(payload, bot, LOG_CHANNEL_ID, MUSIC_CHANNEL_ID, ALLOWED_ROLE_ID):
    await handle_message_delete(payload, bot, LOG_CHANNEL_ID, MUSIC_CHANNEL_ID, ALLOWED_ROLE_ID)
