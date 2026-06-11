import discord
async def handle_member_remove(member, bot, LEAVE_CHANNEL_ID):
    log_channel = bot.get_channel(LEAVE_CHANNEL_ID)
    await log_channel.send(f'**{member.display_name}** hat den Server verlassen.')


async def on_member_remove_handler(member, bot, LEAVE_CHANNEL_ID):
    await handle_member_remove(member, bot, LEAVE_CHANNEL_ID)
