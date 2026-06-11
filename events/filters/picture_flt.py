import discord
import json

async def handler(message):
    with open('./config.json', 'r', encoding="utf-8") as f:
        data = json.load(f)

    picture_channel_id = data['PICTURE_CHANNEL_ID']

    if message.channel.id == picture_channel_id:
        if not message.attachments and not message.reference:
            try:
                await message.author.send(f"Deine Nachricht aus **<#{picture_channel_id}>** wurde gelöscht, bitte sende dort keine Nachrichten, außer **Bilder** oder **Antworten auf Bilder**.")
                await message.delete()
            except discord.Forbidden:
                print("Fehler beim Senden der DM-Nachricht.")
            return False
        elif message.reference and not message.reference.resolved.attachments:
            try:
                await message.author.send(f"Deine Nachricht aus **<#{picture_channel_id}>** wurde gelöscht, bitte sende dort keine Nachrichten, außer **Bilder** oder **Antworten auf Bilder**.")
                await message.delete()
            except discord.Forbidden:
                print("Fehler beim Senden der DM-Nachricht.")
            return True

    return False
