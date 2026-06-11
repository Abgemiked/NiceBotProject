import discord
import json
async def update_statistics(cfg_json, guild):
    with open('config.json') as config_file:
        data = json.load(config_file) 
    total_members = guild.member_count
    role_id = data['IGNORED_ROLE_ID']
    role = guild.get_role(role_id)
    role_members = len(role.members) if role else 0
    members_without_role = total_members - role_members if role_members is not None else total_members

    channel = None
    for voice_channel in guild.voice_channels:
        if voice_channel.name.startswith("Mitglieder:"):
            channel = voice_channel
            break

    if channel is None:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True)
        }
        new_channel = await guild.create_voice_channel("Mitglieder:", overwrites=overwrites)
        print(f"Created new channel: {new_channel.name}")
        channel = new_channel
        await channel.set_permissions(
            guild.default_role,
            view_channel = True,
            manage_channels = False,
            manage_permissions = False,
            manage_webhooks = False,
            create_instant_invite = False,
            connect = False,
            speak= False,
            stream = False,
            use_embedded_activities = False,
            use_soundboard = False,
            use_external_sounds = False,
            use_voice_activation = False,
            mute_members = False,
            deafen_members = False,
            move_members = False,
            send_messages = False,
            embed_links = False,
            attach_files = False,
            add_reactions = False,
            use_external_emojis = False,
            use_external_stickers = False,
            mention_everyone = False,
            manage_messages = False, 
            read_message_history = False,
            send_tts_messages = False,
            use_application_commands = False,
            manage_events = False
        )
    else:
        print(f"Channel already exists: {channel.name}")

    print("Total Members:", total_members)
    print("Role Members:", role_members)
    print("Members Without Role:", members_without_role)

    await channel.edit(name=f"Mitglieder: {members_without_role}")