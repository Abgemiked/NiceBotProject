import discord
import sqlite3

db = sqlite3.connect('level_system.db')
cursor = db.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        exp INTEGER DEFAULT 0,
        level INTEGER DEFAULT 1
    )
''')
db.commit()

async def handler(interaction: discord.Interaction, rang_user: discord.Member=None):
    await interaction.response.defer()
    if rang_user is None:
        rang_user = interaction.user

    user_id = rang_user.id
    cursor.execute('SELECT exp, level FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    if result:
        exp, level = result
        embed = discord.Embed(title=f'Rang von {rang_user.name}', color=discord.Color.green())
        embed.add_field(name='Level', value=str(level), inline=True)
        embed.add_field(name='Erfahrungspunkte', value=str(exp), inline=True)
        await interaction.edit_original_response(embed = embed)
    else:
        await interaction.edit_original_response(content='Der angegebene Benutzer ist nicht in der Datenbank registriert.')
