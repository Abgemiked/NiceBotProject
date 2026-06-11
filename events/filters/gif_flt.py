import discord

from config import load_config


async def handler(message):
    data = load_config()
    gif_channel_id = data['GIF_ID']
    # Chatfilter for GIFs only from tenor
    if message.channel.id == gif_channel_id:
        if message.content and not message.content.startswith("https://tenor.com/"):
            await message.delete()
            try:
                await message.author.send(f"Deine Nachricht aus **<#{gif_channel_id}>** wurde gelöscht, bitte sende dort keine Nachrichten. Der Channel ist nur für **GIFs** gedacht.")
            except discord.Forbidden:
                print("Fehler beim Senden der DM-Nachricht.")
            return True

        if message.attachments:
            for attachment in message.attachments:
                if not attachment.url.startswith("https://tenor.com/"):
                    await message.delete()
                    try:
                        await message.author.send(f"Deine Nachricht aus **<#{gif_channel_id}>** wurde gelöscht, bitte sende dort keine Nachrichten. Der Channel ist nur für **GIFs** gedacht.")
                    except discord.Forbidden:
                        print("Fehler beim Senden der DM-Nachricht.")
                    return True

    return False
