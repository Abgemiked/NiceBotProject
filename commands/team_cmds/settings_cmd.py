import discord
import json

async def handler(interaction: discord.Interaction, allgemein_channel: discord.TextChannel=None, spam_channel: discord.TextChannel=None, keyword: str=None, gif_channel: discord.TextChannel=None, log_channel: discord.TextChannel=None, musiccommand_channel: discord.TextChannel=None, temp_template_channel: discord.VoiceChannel=None, temp_category: discord.CategoryChannel=None,  botcommand_channel: discord.TextChannel=None, adminrole: discord.Role=None, botrole: discord.Role=None, picture_channel: discord.TextChannel=None, api_key_weather: str=None,base_url: str=None, geonames_username: str=None):
    await interaction.response.defer()
    with open('config.json') as config_file:
        data = json.load(config_file)
    variables = [allgemein_channel, spam_channel, keyword, gif_channel, log_channel, musiccommand_channel, temp_template_channel, temp_category, botcommand_channel, adminrole, botrole, picture_channel, api_key_weather, base_url, geonames_username]
    for variable in variables:
        if allgemein_channel is not None:
            data['ALLGEMEIN_ID'] = allgemein_channel.id
        if spam_channel is not None:
            data['SPAM_CHANNEL_ID'] = spam_channel.id
        if keyword is not None:
            data['SPAM_KEYWORD'] = keyword
        if gif_channel is not None:
            data['GIF_ID'] = gif_channel.id
        if log_channel is not None:
            data['LOG_CHANNEL_ID'] = log_channel.id
        if musiccommand_channel is not None:
            data['MUSIC_CHANNEL_ID'] = musiccommand_channel.id
        if picture_channel is not None:
            data['PICTURE_CHANNEL_ID'] = picture_channel.id
        if botcommand_channel is not None:
            data['BOT_CHANNEL_ID'] = botcommand_channel.id
        if temp_template_channel is not None:
            data['TEMP_CHANNEL_ID'] = temp_template_channel.id
        if temp_category is not None:
            data['TEMP_CATEGORY_ID'] = temp_category.id
        if adminrole is not None:
            data['ALLOWED_ROLE_IDS'] = adminrole.id
        if api_key_weather is not None:
            data['API_KEY'] = api_key_weather
        if base_url is not None:
            data['BASE_URL'] = base_url
        if geonames_username is not None:
            data['GEONAMES_API_USERNAME']  = geonames_username
        if botrole is not None:
            data['IGNORED_ROLE_ID'] = botrole.id
    with open('config.json', 'w') as config_file:
        json.dump(data, config_file)
    with open('config.json') as config_file:
        data = json.load(config_file)    
    if all(variable is None for variable in variables):
        embed = discord.Embed(
            title="Aktuelle Einstellungen",
            color=interaction.guild.me.top_role.color,
            timestamp=interaction.created_at
        )
        embed.add_field(name="Allgemeiner Channel", value=f"{data['ALLGEMEIN_ID']}", inline=False)
        embed.add_field(name="Spam Channel", value=f"{data['SPAM_CHANNEL_ID']}", inline=False)
        embed.add_field(name="Spam Schlüsselwort", value=f"{data['SPAM_KEYWORD']}", inline=False)
        embed.add_field(name="Gif Channel", value=f"{data['GIF_ID']}", inline=False)
        embed.add_field(name="Bilderchannel", value=f"{data['PICTURE_CHANNEL_ID']}", inline=False)
        embed.add_field(name="Logchannel", value=f"{data['LOG_CHANNEL_ID']}", inline=False)
        embed.add_field(name="Musikbefehlchannel", value=f"{data['MUSIC_CHANNEL_ID']}", inline=False)
        embed.add_field(name="Temp-Vorlage-Channel", value=f"{data['TEMP_CHANNEL_ID']}", inline=False)
        embed.add_field(name="Temp-Kategorie", value=f"{data['TEMP_CATEGORY_ID']}", inline=False)
        embed.add_field(name="Botbefehlechannel", value=f"{data['BOT_CHANNEL_ID']}", inline=False)
        embed.add_field(name="eingeschränkte Rollen", value=f"{data['BLOCKED_CHANNEL_IDS']}", inline=False)
        embed.add_field(name="Admninrolle", value=f"{data['ALLOWED_ROLE_IDS']}", inline=False)
        embed.add_field(name="Botrolle bzgl. Userzahl", value=f"{data['IGNORED_ROLE_ID']}", inline=False)
        embed.add_field(name="API-Key für Wetter", value=f"{data['API_KEY']}", inline=False)
        embed.add_field(name="BASE-URL für Wetter", value=f"{data['BASE_URL']}", inline=False)
        embed.add_field(name="GEONAMES Username für Wetter", value=f"{data['GEONAMES_API_USERNAME']}", inline=False)
        await interaction.edit_original_response(embed=embed)
        return
    else:
        await interaction.edit_original_response(content="Die Servereinstellungen wurden aktualisiert.")