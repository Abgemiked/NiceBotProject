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
def calculate_exp(level):
    if level <= 5:
        return 100
    elif level <= 15:
        return 100
    elif level <= 25:
        return 125
    elif level <= 50:
        return 250
    elif level <= 75:
        return 375
    elif level <= 100:
        return 500
    elif level <= 125:
        return 625
    elif level <= 150:
        return 750
    elif level <= 175:
        return 875
    else:
        return 1000

async def handler(interaction: discord.Interaction, rang_user_give: discord.Member, lvl: int):
    # Code zur Überprüfung und Verarbeitung des Ranggeschenks
    await interaction.response.defer()
    cursor.execute('SELECT exp, level FROM users WHERE user_id = ?', (rang_user_give.id,))
    result = cursor.fetchone()
    if result:
        _, level = result
        level = lvl
        await interaction.edit_original_response(content=f"{rang_user_give.mention} hat nun Level {level}!")

        cursor.execute('UPDATE users SET level = ? WHERE user_id = ?', (level, rang_user_give.id))
    else:
        cursor.execute('INSERT INTO users (user_id, exp, level) VALUES (?, ?, ?)', (rang_user_give.id, 0, lvl))

    db.commit()