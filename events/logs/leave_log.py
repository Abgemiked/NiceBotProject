import discord

import audit_log


async def handle_member_remove(member, bot, LEAVE_CHANNEL_ID):
    # Audit zuerst (unabhängig davon, ob der Log-Channel erreichbar ist).
    audit_log.log_event(
        "member_leave",
        target_id=member.id,
        target_name=member.display_name,
    )
    log_channel = bot.get_channel(LEAVE_CHANNEL_ID)
    if log_channel is None:
        return
    await log_channel.send(f'**{member.display_name}** hat den Server verlassen.')


async def on_member_remove_handler(member, bot, LEAVE_CHANNEL_ID):
    await handle_member_remove(member, bot, LEAVE_CHANNEL_ID)
