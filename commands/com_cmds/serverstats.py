import discord

from config import load_config


async def handler(interaction: discord.Interaction):
    data = load_config()
    await interaction.response.defer()
    role_id = data['IGNORED_ROLE_ID']
    guild = interaction.guild
    total_members = guild.member_count
    role = guild.get_role(role_id)
    role_members = len(role.members) if role else 0
    members_without_role = total_members - role_members
    embed = discord.Embed(title="Server Statistik")
    embed.add_field(name="Gesamtnutzer:", value=total_members, inline=False)
    embed.add_field(name="Mitglieder ohne Bots", value=members_without_role, inline=False)
    await interaction.edit_original_response(embed=embed)
