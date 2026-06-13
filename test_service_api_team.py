"""Smoke-/Logik-Test für Stage B (Team-Channels + Team-Rollen-Guards).

Standalone (kein pytest in der venv): aiohttp-TestClient gegen die echte
create_service_app, Bot/Guild/Member/Channel sind leichte Fakes. Geprüft:

  - team role-assign/role-remove mit Nicht-Team-Rolle  → 403, KEIN add/remove
  - team role-assign mit "-Leader"/"-Member"-Rolle      → 200, add läuft
  - Team-Rolle >= Bot-Top-Rolle (trotz Suffix)          → 403
  - POST /internal/teams/discord: Rollen-Wiederverwendung (existing_*)
  - POST /internal/teams/discord: Rollen-Neuanlage + Channel-Erstellung
  - DELETE /internal/teams/discord: delete_roles=false → nur Channels weg
  - DELETE /internal/teams/discord: delete_roles=true  → auch Rollen weg

Ausführen:  .venv\\Scripts\\python.exe test_service_api_team.py
"""
import asyncio
import sys

from aiohttp.test_utils import TestClient, TestServer

from service_api import (
    TEAM_ROLE_LEADER_SUFFIX,
    TEAM_ROLE_MEMBER_SUFFIX,
    create_service_app,
)

import discord  # noqa: F401  (für CategoryChannel-isinstance im Endpoint)

TOKEN = "test-secret"
GUILD_ID = 123
EM_ROLE_ID = 22222
CATEGORY_ID = 1128924760642965564


class FakeRole:
    def __init__(self, role_id, name, position):
        self.id = role_id
        self.name = name
        self.position = position
        self.deleted = False

    def __ge__(self, other):
        return self.position >= other.position

    def __lt__(self, other):
        return self.position < other.position

    async def delete(self, reason=None):
        self.deleted = True


class FakeMember:
    def __init__(self, member_id=0, top_role=None):
        self.id = member_id
        self.top_role = top_role
        self.added = []
        self.removed = []

    async def add_roles(self, role, reason=None):
        self.added.append(role)

    async def remove_roles(self, role, reason=None):
        self.removed.append(role)


class FakeCategory(discord.CategoryChannel):
    def __init__(self, channel_id, guild):
        self.id = channel_id
        self.guild = guild


class FakeChannel:
    def __init__(self, channel_id, guild):
        self.id = channel_id
        self.guild = guild
        self.deleted = False

    async def delete(self, reason=None):
        self.deleted = True


class FakeGuild:
    def __init__(self, roles, members, channels, bot_top_role):
        self.id = GUILD_ID
        self._roles = {r.id: r for r in roles}
        self._members = members
        self._channels = {c.id: c for c in channels}
        self.me = FakeMember(top_role=bot_top_role)
        self.default_role = FakeRole(0, "@everyone", position=0)
        self._next_role_id = 70000
        self._next_chan_id = 80000
        self.created_roles = []
        self.created_text = []
        self.created_voice = []

    def get_role(self, role_id):
        return self._roles.get(role_id)

    def get_member(self, member_id):
        return self._members.get(member_id)

    def get_channel(self, channel_id):
        return self._channels.get(channel_id)

    async def create_role(self, name, mentionable=False, hoist=False, reason=None):
        self._next_role_id += 1
        role = FakeRole(self._next_role_id, name, position=5)
        self._roles[role.id] = role
        self.created_roles.append(role)
        return role

    async def create_text_channel(self, name, category=None, overwrites=None, reason=None):
        self._next_chan_id += 1
        ch = FakeChannel(self._next_chan_id, self)
        ch.overwrites = overwrites
        self._channels[ch.id] = ch
        self.created_text.append(ch)
        return ch

    async def create_voice_channel(self, name, category=None, overwrites=None, reason=None):
        self._next_chan_id += 1
        ch = FakeChannel(self._next_chan_id, self)
        ch.overwrites = overwrites
        self._channels[ch.id] = ch
        self.created_voice.append(ch)
        return ch


class FakeBot:
    def __init__(self, guild):
        self._guild = guild

    def get_guild(self, guild_id):
        return self._guild if guild_id == GUILD_ID else None

    async def fetch_channel(self, channel_id):
        raise discord.NotFound.__new__(discord.NotFound)


def build_app(guild):
    return create_service_app(
        {
            "TURNIER_SERVICE_TOKEN": TOKEN,
            "GUILD_ID": GUILD_ID,
            "TURNIER_EM_ROLE_ID": EM_ROLE_ID,
        },
        FakeBot(guild),
    )


async def main():
    failures = []

    def check(label, cond):
        print(("PASS  " if cond else "FAIL  ") + label)
        if not cond:
            failures.append(label)

    bot_top = FakeRole(900, "NiceBot", position=50)
    em_role = FakeRole(EM_ROLE_ID, "Eventmanagement", position=40)
    leader_role = FakeRole(11111, "Alpha" + TEAM_ROLE_LEADER_SUFFIX, position=5)
    member_role = FakeRole(11112, "Alpha" + TEAM_ROLE_MEMBER_SUFFIX, position=5)
    high_team = FakeRole(33333, "Hoch" + TEAM_ROLE_LEADER_SUFFIX, position=99)
    member = FakeMember(member_id=55555)
    leader_member = FakeMember(member_id=44444)

    guild = FakeGuild(
        roles=[em_role, leader_role, member_role, high_team],
        members={55555: member, 44444: leader_member},
        channels=[],
        bot_top_role=bot_top,
    )
    guild._channels[CATEGORY_ID] = FakeCategory(CATEGORY_ID, guild)

    async with TestClient(TestServer(build_app(guild))) as client:
        H = {"X-Service-Token": TOKEN}

        # --- Team-Rollen-Guard ---
        res = await client.post(
            "/internal/teams/discord/role-assign",
            json={"role_id": str(em_role.id), "discord_id": "55555"}, headers=H,
        )
        body = await res.json()
        check("team role-assign EM-Rolle → 403", res.status == 403)
        check("team role-assign EM-Rolle → KEIN add", member.added == [])

        res = await client.post(
            "/internal/teams/discord/role-assign",
            json={"role_id": str(high_team.id), "discord_id": "55555"}, headers=H,
        )
        check("team role-assign über Bot-Top → 403", res.status == 403)

        res = await client.post(
            "/internal/teams/discord/role-assign",
            json={"role_id": str(member_role.id), "discord_id": "55555"}, headers=H,
        )
        body = await res.json()
        check("team role-assign Member-Rolle → 200", res.status == 200 and body.get("ok"))
        check("team role-assign Member-Rolle → add", member.added == [member_role])

        res = await client.post(
            "/internal/teams/discord/role-remove",
            json={"role_id": str(member_role.id), "discord_id": "55555"}, headers=H,
        )
        check("team role-remove Member-Rolle → remove", member.removed == [member_role])

        # --- POST: Rollen-Wiederverwendung (existing_*) ---
        before_roles = len(guild.created_roles)
        res = await client.post(
            "/internal/teams/discord",
            json={
                "tournament_category_id": str(CATEGORY_ID),
                "team_name": "Alpha",
                "leader_discord_id": "44444",
                "member_discord_ids": ["55555"],
                "existing_leader_role_id": str(leader_role.id),
                "existing_member_role_id": str(member_role.id),
            },
            headers=H,
        )
        body = await res.json()
        check("teams POST (existing) → 201", res.status == 201)
        check("teams POST (existing) → KEINE neuen Rollen",
              len(guild.created_roles) == before_roles)
        check("teams POST (existing) → leader_role_id wiederverwendet",
              body.get("leader_role_id") == str(leader_role.id))
        check("teams POST (existing) → Text+Voice angelegt",
              body.get("text_channel_id") and body.get("voice_channel_id"))
        check("teams POST (existing) → Leader bekam Leader-Rolle",
              leader_role in leader_member.added)
        check("teams POST (existing) → Member bekam Member-Rolle",
              member_role in member.added)

        # --- POST: Rollen-Neuanlage ---
        before_roles = len(guild.created_roles)
        res = await client.post(
            "/internal/teams/discord",
            json={
                "tournament_category_id": str(CATEGORY_ID),
                "team_name": "Beta",
                "leader_discord_id": "44444",
                "member_discord_ids": [],
            },
            headers=H,
        )
        body = await res.json()
        check("teams POST (neu) → 201", res.status == 201)
        check("teams POST (neu) → 2 neue Rollen angelegt",
              len(guild.created_roles) == before_roles + 2)

        new_text = body["text_channel_id"]
        new_voice = body["voice_channel_id"]
        new_leader = body["leader_role_id"]
        new_member = body["member_role_id"]

        # @everyone darf NICHT sichtbar sein (kein Leak)
        last_text = guild.created_text[-1]
        everyone_ov = last_text.overwrites.get(guild.default_role)
        check("teams POST (neu) → @everyone view_channel=False",
              everyone_ov is not None and everyone_ov.view_channel is False)

        # --- DELETE: delete_roles=false → nur Channels ---
        res = await client.request(
            "DELETE", "/internal/teams/discord",
            json={
                "text_channel_id": new_text,
                "voice_channel_id": new_voice,
                "leader_role_id": new_leader,
                "member_role_id": new_member,
                "delete_roles": False,
            },
            headers=H,
        )
        body = await res.json()
        check("teams DELETE (keep roles) → 200", res.status == 200)
        check("teams DELETE (keep roles) → beide Channels deleted",
              new_text in body["deleted"] and new_voice in body["deleted"])
        check("teams DELETE (keep roles) → Rolle NICHT deleted",
              guild.get_role(int(new_leader)) is not None
              and not guild.get_role(int(new_leader)).deleted)

        # --- DELETE: delete_roles=true → auch Rollen ---
        res = await client.request(
            "DELETE", "/internal/teams/discord",
            json={
                "text_channel_id": None,
                "voice_channel_id": None,
                "leader_role_id": new_leader,
                "member_role_id": new_member,
                "delete_roles": True,
            },
            headers=H,
        )
        body = await res.json()
        check("teams DELETE (delete roles) → 200", res.status == 200)
        check("teams DELETE (delete roles) → beide Rollen deleted",
              new_leader in body["deleted"] and new_member in body["deleted"])

    if failures:
        print(f"\n{len(failures)} Check(s) FEHLGESCHLAGEN")
        return 1
    print("\nAlle Checks PASS")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
