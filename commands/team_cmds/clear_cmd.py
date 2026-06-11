import discord

async def handler(cfg_json, interaction, amount):
    if amount < 1 or amount > 20:
        await interaction.response.send_message(content="Die Anzahl der zu löschenden Nachrichten muss zwischen **1** und **20** liegen.")
        return
    
    channel = interaction.channel
    messages = []
    
    async for message in channel.history(limit=amount + 1):
        messages.append(message)
    
    if messages:
        await interaction.response.defer()
        log_channel = interaction.guild.get_channel(cfg_json['LOG_CHANNEL_ID'])
        
        if log_channel is not None:
            for message in messages:
                await log_channel.send(f'Die Nachricht "**{message.content}**" von **{message.author.name}** wurde aus dem **{message.channel.name}** gelöscht.')
        
        await channel.delete_messages(messages)
        await interaction.edit_original_response(content="Die Nachrichten wurden gelöscht")
    else:
        await interaction.response.send_message(content="**Du hast nicht die Berechtigung, Nachrichten zu löschen!**")
