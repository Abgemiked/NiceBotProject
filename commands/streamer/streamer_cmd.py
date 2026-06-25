from commands.streamer import streamer_core


async def handler(cfg_json, interaction, streamer_name):
    await interaction.response.defer()
    display = await streamer_core.create_streamer(interaction.guild, streamer_name.name)
    await interaction.edit_original_response(
        content=f"Die Kategorie, Channel & Rollen für **{display}** wurden eingerichtet & können verwendet werden."
    )
