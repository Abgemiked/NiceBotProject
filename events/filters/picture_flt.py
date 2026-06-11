import discord

from config import load_config


async def handler(message):
    data = load_config()
    picture_channel_id = data['PICTURE_CHANNEL_ID']

    if message.channel.id == picture_channel_id:
        if not message.attachments and not message.reference:
            await message.delete()
            try:
                await message.author.send(f"Deine Nachricht aus **<#{picture_channel_id}>** wurde gelöscht, bitte sende dort keine Nachrichten, außer **Bilder** oder **Antworten auf Bilder**.")
            except discord.Forbidden:
                print("Fehler beim Senden der DM-Nachricht.")
            return True
        if message.reference:
            resolved = message.reference.resolved
            if resolved is None:
                # Referenz nicht im Cache auflösbar -> im Zweifel nicht löschen
                return False
            if isinstance(resolved, discord.DeletedReferencedMessage) or not resolved.attachments:
                await message.delete()
                try:
                    await message.author.send(f"Deine Nachricht aus **<#{picture_channel_id}>** wurde gelöscht, bitte sende dort keine Nachrichten, außer **Bilder** oder **Antworten auf Bilder**.")
                except discord.Forbidden:
                    print("Fehler beim Senden der DM-Nachricht.")
                return True

    return False
