import discord

from database import get_connection


async def handler(interaction: discord.Interaction):
    await interaction.response.defer()
    bot = interaction.client
    cursor = get_connection().cursor()
    cursor.execute('SELECT user_id, exp, level FROM users ORDER BY level DESC LIMIT 20')
    result = cursor.fetchall()
    embed = discord.Embed(title='Rangliste', color=discord.Color.gold())
    for row in result:
        user_id, exp, level = row
        user = bot.get_user(user_id)
        if user:
            embed.add_field(name=f'{user.name} (Level {level})', value=f'Erfahrungspunkte: {exp}', inline=False)
        else:
            embed.add_field(name=f'Unbekannter Nutzer (Level {level})', value=f'Erfahrungspunkte: {exp}', inline=False)

    await interaction.edit_original_response(embed=embed)
