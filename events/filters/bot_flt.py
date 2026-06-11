import discord
import json
async def handler(message):
    with open('./config.json', 'r', encoding="utf-8") as f:
        data = json.load(f)
    BOT_CHANNEL_ID = data['BOT_CHANNEL_ID']
    bot_role_id = data['IGNORED_ROLE_ID']
    if message.channel.id != BOT_CHANNEL_ID:
        return
    if message.content and message.content.startswith('/'):
        return
    if isinstance(message.author, discord.Member) and any(role.id == bot_role_id for role in message.author.roles):
        return
    if isinstance(message.author, discord.Member) and not isinstance(message.author, discord.ClientUser):
        try:
            await message.author.send(f"Deine Nachricht aus **<#{BOT_CHANNEL_ID}>** wurde gelöscht, bitte sende dort keine Nachrichten. Der Channel ist nur für **/-Befehle** gedacht.")
            await message.delete()
        except discord.Forbidden:
            print("Fehler beim Senden der DM-Nachricht.")    