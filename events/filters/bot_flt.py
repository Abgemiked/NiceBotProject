import discord

from config import load_config


async def handler(message):
    # Bot-Nachrichten (auch eigene Slash-Command-Antworten) nie filtern —
    # eine DM an einen Bot/sich selbst ist nicht möglich (ClientUser hat kein create_dm)
    if message.author.bot:
        return False
    data = load_config()
    BOT_CHANNEL_ID = data['BOT_CHANNEL_ID']
    bot_role_id = data['IGNORED_ROLE_ID']
    if message.channel.id != BOT_CHANNEL_ID:
        return False
    if message.content and message.content.startswith('/'):
        return False
    if isinstance(message.author, discord.Member) and any(role.id == bot_role_id for role in message.author.roles):
        return False
    if isinstance(message.author, discord.Member):
        try:
            await message.author.send(f"Deine Nachricht aus **<#{BOT_CHANNEL_ID}>** wurde gelöscht, bitte sende dort keine Nachrichten. Der Channel ist nur für **/-Befehle** gedacht.")
        except discord.HTTPException:
            print("Fehler beim Senden der DM-Nachricht.")
        await message.delete()
        return True
    return False
