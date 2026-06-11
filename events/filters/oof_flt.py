import discord

from config import load_config


async def handler(message):
    data = load_config()
    spam_channel_id = data['SPAM_CHANNEL_ID']
    keyword = data['SPAM_KEYWORD']
    if message.channel.id == spam_channel_id:
        if message.content != keyword:
            await message.delete()
            try:
                await message.author.send(f"Deine Nachricht aus **<#{spam_channel_id}>** wurde gelöscht, bitte sende dort keine Nachrichten. Der Channel ist nur für das Wort **{keyword}** gedacht.")
            except discord.Forbidden:
                print("Fehler beim Senden der DM-Nachricht.")
            return True
    return False
