import discord
import json
async def handler(message):
    with open('./config.json', 'r', encoding="utf-8") as f:
        data = json.load(f)
    gif_channel_id = data['GIF_ID']
    #Chatfilter for GIFs only from tenor
    if message.channel.id == gif_channel_id:
        if message.content and not message.content.startswith("https://tenor.com/"):
            await message.delete()
            try:
                await message.author.send(f"Deine Nachricht aus **<#{gif_channel_id}>** wurde gelöscht, bitte sende dort keine Nachrichten. Der Channel ist nur für **GIFs** gedacht.")
            except discord.Forbidden:
                print("Fehler beim Senden der DM-Nachricht.")
            return

        if message.attachments:
            for attachment in message.attachments:
                if not attachment.url.startswith("https://tenor.com/"):
                    await message.delete()
                    try:
                        await message.author.send(f"Deine Nachricht aus **<#{gif_channel_id}>** wurde gelöscht, bitte sende dort keine Nachrichten. Der Channel ist nur für **GIFs** gedacht.")
                    except discord.Forbidden:
                        print("Fehler beim Senden der DM-Nachricht.")
                    return

    return False
                                 