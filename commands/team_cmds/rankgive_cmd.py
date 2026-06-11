import discord

from database import get_connection


async def handler(interaction: discord.Interaction, rang_user_give: discord.Member, lvl: int):
    await interaction.response.defer()
    db = get_connection()
    cursor = db.cursor()
    cursor.execute('SELECT exp, level FROM users WHERE user_id = ?', (rang_user_give.id,))
    result = cursor.fetchone()
    if result:
        cursor.execute('UPDATE users SET level = ? WHERE user_id = ?', (lvl, rang_user_give.id))
    else:
        cursor.execute('INSERT INTO users (user_id, exp, level) VALUES (?, ?, ?)', (rang_user_give.id, 0, lvl))
    db.commit()
    await interaction.edit_original_response(content=f"{rang_user_give.mention} hat nun Level {lvl}!")
