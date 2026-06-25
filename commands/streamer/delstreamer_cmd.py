from commands.streamer import streamer_core


async def handler(cfg_json, interaction, streamer):
    name = streamer.name.capitalize()
    if not streamer_core.streamer_exists(interaction.guild, streamer.name):
        await interaction.response.send_message(
            content=f"Die Kategorie für **{name}** existiert nicht."
        )
        return
    await interaction.response.defer()
    await streamer_core.delete_streamer(interaction.guild, streamer.name)
    await interaction.edit_original_response(content=f"Die Kategorie von **{name}** wurde gelöscht.")
