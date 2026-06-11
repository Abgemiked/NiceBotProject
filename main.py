import asyncio

import discord
from discord import app_commands

from config import load_config
from database import get_connection, calculate_exp
from commands.com_cmds.limit_cmd import handler as limit_cmd
from commands.streamer.streamer_cmd import handler as streamer_cmd
from commands.streamer.delstreamer_cmd import handler as delstreamer_cmd
from commands.team_cmds.clear_cmd import handler as clear_cmd
from commands.com_cmds.weather_cmd import handler as weather_cmd
from commands.team_cmds.settings_cmd import handler as settings_cmd
from commands.com_cmds.serverstats import handler as serverstats_cmd
from commands.help_cmd import handler as hilfe_cmd
from commands.com_cmds.ranklist_cmd import handler as ranklist_cmd
from commands.com_cmds.rank_cmd import handler as rank_cmd
from commands.team_cmds.rankgive_cmd import handler as rankgive_cmd
from events.message_event import handler as message_handler
from events.logs.delete_log import on_raw_message_delete_handler
from events.logs.leave_log import on_member_remove_handler
from events.temp_channel.voice_temp import on_voice_state_update_handler
from events.temp_channel.voice_temp import handle_empty_temp_channels
from events.statistic_channel.statistic import update_statistics

cfg_json = load_config()

intents = discord.Intents(65419)
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

_statistics_loop_started = False


@bot.event
async def on_ready():
    global _statistics_loop_started
    await tree.sync()
    print("Ready!")
    if not _statistics_loop_started:
        _statistics_loop_started = True
        asyncio.create_task(update_statistics_loop())


async def update_statistics_loop():
    while True:
        guild = bot.get_guild(cfg_json['GUILD_ID'])
        if guild:
            asyncio.create_task(update_statistics(cfg_json, guild))
        await asyncio.sleep(300)


@tree.command(description="Frag nach Hilfe")
async def hilfe(interaction: discord.Interaction):
    await hilfe_cmd(interaction)


@tree.command(description="Kategorie für Streamer erstellen")
async def streamer(interaction: discord.Interaction, streamer_name: discord.Member):
    await streamer_cmd(cfg_json, interaction, streamer_name)


@tree.command(description="Lösche Kategorie, Kanäle und Rollen für einen Streamer")
async def streamer_löschen(interaction: discord.Interaction, streamer: discord.Member):
    await delstreamer_cmd(cfg_json, interaction, streamer)


@tree.command(description="Nutzerlimit für den aktuellen Talk ändern")
async def limit(interaction: discord.Interaction, limit: int):
    await limit_cmd(cfg_json, interaction, limit)


@tree.command(description="Löscht eine angegebene Anzahl an Nachrichten im Channel")
async def löschen(interaction: discord.Interaction, amount: int):
    await clear_cmd(cfg_json, interaction, amount)


@tree.command(description="Hier kannst du das Wetter für deine Ortschaft abfragen")
async def wetter(interaction: discord.Interaction, ort: str):
    await weather_cmd(interaction, ort)


@tree.command(description="Servereinrichtung anpassen")
async def einstellungen(interaction: discord.Interaction, allgemein_channel: discord.TextChannel = None, spam_channel: discord.TextChannel = None, keyword: str = None, gif_channel: discord.TextChannel = None, log_channel: discord.TextChannel = None, musiccommand_channel: discord.TextChannel = None, temp_template_channel: discord.VoiceChannel = None, temp_category: discord.CategoryChannel = None, botcommand_channel: discord.TextChannel = None, adminrole: discord.Role = None, botrole: discord.Role = None, picture_channel: discord.TextChannel = None):
    await settings_cmd(interaction, allgemein_channel, spam_channel, keyword, gif_channel, log_channel, musiccommand_channel, temp_template_channel, temp_category, botcommand_channel, adminrole, botrole, picture_channel)


@tree.command(description="Zeigt die aktuellen Nutzer ohne Bots an")
async def serverstats(interaction: discord.Interaction):
    await serverstats_cmd(interaction)


@tree.command(description="Zeigt die Rangliste des Levelsystem an")
async def rangliste(interaction: discord.Interaction):
    await ranklist_cmd(interaction)


@tree.command(description="Zeigt den Rang des angegebenen Users an")
async def rang(interaction: discord.Interaction, rang_user: discord.Member = None):
    await rank_cmd(interaction, rang_user)


@tree.command(description="Gibt einem Benutzer ein bestimmte Level")
async def rang_geben(interaction: discord.Interaction, rang_user_give: discord.Member, lvl: int):
    await rankgive_cmd(interaction, rang_user_give, lvl)


@bot.event
async def on_message(message):
    await message_handler(cfg_json, message)
    if message.author.bot:
        return
    db = get_connection()
    cursor = db.cursor()
    user_id = message.author.id
    cursor.execute('SELECT exp, level FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()

    if result:
        exp, level = result
        exp += 1

        required_exp = calculate_exp(level)
        if exp >= required_exp:
            bot_channel = bot.get_channel(cfg_json['BOT_CHANNEL_ID'])
            level += 1
            exp = 0
            if bot_channel:
                await bot_channel.send(f'Glückwunsch, {message.author.mention}! Du hast Level {level} erreicht!')
        cursor.execute('UPDATE users SET exp = ?, level = ? WHERE user_id = ?', (exp, level, user_id))
    else:
        cursor.execute('INSERT INTO users (user_id) VALUES (?)', (user_id,))
    db.commit()


@bot.event
async def on_raw_message_delete(payload):
    await on_raw_message_delete_handler(payload, bot, cfg_json['LOG_CHANNEL_ID'], cfg_json['MUSIC_CHANNEL_ID'], cfg_json['ALLOWED_ROLE_IDS'])


@bot.event
async def on_member_remove(member):
    await on_member_remove_handler(member, bot, cfg_json['LEAVE_CHANNEL_ID'])


@bot.event
async def on_voice_state_update(member, before, after):
    guild = member.guild
    if before.channel and before.channel.category_id == cfg_json["TEMP_CATEGORY_ID"]:
        await handle_empty_temp_channels(guild)
    await on_voice_state_update_handler(member, before, after, guild)


if __name__ == "__main__":
    token = cfg_json.get("TOKEN")
    if not token:
        raise SystemExit("Kein Bot-Token gefunden: Setze NICEBOT_TOKEN/TOKEN als Umgebungsvariable oder trage TOKEN in config.json ein.")
    bot.run(token)
