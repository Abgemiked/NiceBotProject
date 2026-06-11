import discord
import json
import asyncio
with open('./config.json', 'r', encoding= "utf-8") as f:
    cfg_json = json.load(f)

async def handle_voice_temp(member, before, after):
    TEMP_CHANNEL_ID = cfg_json["TEMP_CHANNEL_ID"]
    temp_channel = member.guild.get_channel(TEMP_CHANNEL_ID)
    if after.channel is not None and after.channel.id == TEMP_CHANNEL_ID:
        guild = member.guild
        channel_name = member.name.capitalize()
        category = after.channel.category
        temp_channel = await category.create_voice_channel(name=channel_name)
        await member.move_to(temp_channel)
        await temp_channel.set_permissions(
            member,  
            view_channel = True,
            manage_channels = True,
            manage_permissions = True,
            manage_webhooks = False,
            create_instant_invite = True,
            connect = True,
            speak= True,
            stream = True,
            use_embedded_activities = True,
            use_soundboard = True,
            use_external_sounds = True,
            use_voice_activation = True,
            mute_members = True,
            deafen_members = True,
            move_members = True,
            send_messages = True,
            embed_links = True,
            attach_files = True,
            add_reactions = True,
            use_external_emojis = True,
            use_external_stickers = True,
            mention_everyone = False,
            manage_messages = True, 
            read_message_history = True,
            send_tts_messages = True,
            use_application_commands = True,
            manage_events = False
        )
        await temp_channel.set_permissions(
            guild.default_role,
            view_channel = True,
            manage_channels = False,
            manage_permissions = False,
            manage_webhooks = False,
            create_instant_invite = True,
            connect = True,
            speak= True,
            stream = True,
            use_embedded_activities = True,
            use_soundboard = True,
            use_external_sounds = True,
            use_voice_activation = True,
            mute_members = False,
            deafen_members = False,
            move_members = False,
            send_messages = True,
            embed_links = True,
            attach_files = True,
            add_reactions = True,
            use_external_emojis = True,
            use_external_stickers = True,
            mention_everyone = False,
            manage_messages = False, 
            read_message_history = True,
            send_tts_messages = True,
            use_application_commands = False,
            manage_events = False
        )
    if before.channel is not None and before.channel.id != TEMP_CHANNEL_ID and len(before.channel.members) == 0:
        temp_channel = discord.utils.get(member.guild.voice_channels, name=member.name.capitalize())
        if temp_channel is not None and before.channel == temp_channel:
            await before.channel.delete()
async def handle_empty_temp_channels(guild):
    TEMP_CATEGORY_ID = cfg_json["TEMP_CATEGORY_ID"]
    TEMP_CHANNEL_ID = cfg_json["TEMP_CHANNEL_ID"]

    temp_category = discord.utils.get(guild.categories, id=TEMP_CATEGORY_ID)
    for channel in temp_category.channels:
        if isinstance(channel, discord.VoiceChannel) and channel.id != TEMP_CHANNEL_ID and len(channel.members) == 0:
            await channel.delete()

async def on_voice_state_update_handler(member, before, after, guild):
    await handle_voice_temp(member, before, after)
    await handle_empty_temp_channels(guild)