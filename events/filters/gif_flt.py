from urllib.parse import urlparse

import discord

from config import load_config, DEFAULT_GIF_ALLOWED_DOMAINS


def _is_allowed_gif_url(content, allowed_domains):
    """True, wenn der gesamte Inhalt genau EINE https-URL eines erlaubten
    GIF-Providers ist.

    Geprüft wird der exakte Host (oder eine Subdomain davon), nicht ein roher
    String-Präfix. Das verhindert sowohl Host-Spoofing (z.B.
    ``https://tenor.com.evil.com/``) als auch angehängte Fremdlinks
    (z.B. ``https://tenor.com/ https://evil.com``), da Whitespace/mehrere
    Tokens den Inhalt ungültig machen.
    """
    url = content.strip()
    if not url or any(ch.isspace() for ch in url):
        return False
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        return False
    host = parsed.hostname.lower()
    return any(host == d or host.endswith("." + d) for d in allowed_domains)


async def handler(message):
    data = load_config()
    gif_channel_id = data['GIF_ID']
    # Im GIF-Channel sind nur GIF-Provider-URLs erlaubt (konfigurierbar via
    # GIF_ALLOWED_DOMAINS in config.json, Default siehe config.DEFAULT_GIF_ALLOWED_DOMAINS).
    allowed_domains = data.get("GIF_ALLOWED_DOMAINS") or DEFAULT_GIF_ALLOWED_DOMAINS
    if message.channel.id == gif_channel_id:
        if message.content and not _is_allowed_gif_url(message.content, allowed_domains):
            await message.delete()
            try:
                await message.author.send(f"Deine Nachricht aus **<#{gif_channel_id}>** wurde gelöscht, bitte sende dort keine Nachrichten. Der Channel ist nur für **GIFs** gedacht.")
            except discord.Forbidden:
                print("Fehler beim Senden der DM-Nachricht.")
            return True

        if message.attachments:
            for attachment in message.attachments:
                if not _is_allowed_gif_url(attachment.url, allowed_domains):
                    await message.delete()
                    try:
                        await message.author.send(f"Deine Nachricht aus **<#{gif_channel_id}>** wurde gelöscht, bitte sende dort keine Nachrichten. Der Channel ist nur für **GIFs** gedacht.")
                    except discord.Forbidden:
                        print("Fehler beim Senden der DM-Nachricht.")
                    return True

    return False
