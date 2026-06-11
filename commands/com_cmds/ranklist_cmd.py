import discord

from database import get_connection

GONE_SUFFIX = ' (nicht mehr auf dem Server)'


async def _resolve_name(bot, guild, db, user_id, stored_username):
    """Anzeigename für einen Ranglisten-Eintrag ermitteln.

    Reihenfolge:
    1. Mitglied noch auf dem Server -> aktueller Discord-Name (wie bisher)
    2. Gespeicherter Username aus der DB -> mit Hinweis-Suffix
    3. Lazy Backfill für Bestandsdaten: einmalig fetch_user (funktioniert
       auch für Ex-Mitglieder), Ergebnis in der DB cachen
    4. Fallback: "Unbekannt" mit Suffix
    """
    member = guild.get_member(user_id) if guild else None
    if member is None and guild is not None:
        # get_member greift nur auf den Cache zu — bei nicht gechunkter
        # Guild kann ein vorhandenes Mitglied fehlen, daher get_user dazu.
        user = bot.get_user(user_id)
        if user is not None:
            member = user
    if member is not None:
        return member.name

    if stored_username:
        return f'{stored_username}{GONE_SUFFIX}'

    # Bestandsdaten ohne gespeicherten Namen: einmalig nachschlagen und cachen
    try:
        fetched = await bot.fetch_user(user_id)
        db.execute('UPDATE users SET username = ? WHERE user_id = ?', (fetched.name, user_id))
        db.commit()
        return f'{fetched.name}{GONE_SUFFIX}'
    except discord.HTTPException:
        return f'Unbekannt{GONE_SUFFIX}'


async def handler(interaction: discord.Interaction):
    await interaction.response.defer()
    bot = interaction.client
    guild = interaction.guild
    db = get_connection()
    cursor = db.cursor()
    cursor.execute('SELECT user_id, exp, level, username FROM users ORDER BY level DESC LIMIT 20')
    result = cursor.fetchall()
    embed = discord.Embed(title='Rangliste', color=discord.Color.gold())
    for user_id, exp, level, stored_username in result:
        name = await _resolve_name(bot, guild, db, user_id, stored_username)
        embed.add_field(name=f'{name} (Level {level})', value=f'Erfahrungspunkte: {exp}', inline=False)

    await interaction.edit_original_response(embed=embed)
