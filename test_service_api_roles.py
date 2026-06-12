"""Smoke-/Logik-Test für die Rollen-Guards der Service-API (Audit A.5/F1).

Standalone (kein pytest in der venv): aiohttp-TestClient gegen die echte
create_service_app, Bot/Guild/Member sind leichte Fakes. Geprüft:

  - role-assign/role-remove mit Nicht-Teilnehmer-Rolle → 403, KEIN add/remove
  - role-assign/role-remove mit Teilnehmer-Rolle       → 200, add/remove läuft
  - Rolle >= Bot-Top-Rolle (trotz Teilnehmer-Präfix)   → 403
  - unbekannte Rolle                                   → 404

Ausführen:  .venv\\Scripts\\python.exe test_service_api_roles.py
(Windows-cp1252-Konsole: vorher  set PYTHONIOENCODING=utf-8)
"""
import asyncio
import sys

from aiohttp.test_utils import TestClient, TestServer

from service_api import PARTICIPANT_ROLE_PREFIX, create_service_app

TOKEN = "test-secret"
GUILD_ID = 123


class FakeRole:
    def __init__(self, role_id, name, position):
        self.id = role_id
        self.name = name
        self.position = position

    # discord.Role vergleicht über die Position in der Rollen-Hierarchie
    def __ge__(self, other):
        return self.position >= other.position

    def __lt__(self, other):
        return self.position < other.position


class FakeMember:
    def __init__(self, top_role=None):
        self.top_role = top_role
        self.added = []
        self.removed = []

    async def add_roles(self, role, reason=None):
        self.added.append(role)

    async def remove_roles(self, role, reason=None):
        self.removed.append(role)


class FakeGuild:
    def __init__(self, roles, members, bot_top_role):
        self._roles = {r.id: r for r in roles}
        self._members = members
        self.me = FakeMember(top_role=bot_top_role)

    def get_role(self, role_id):
        return self._roles.get(role_id)

    def get_member(self, member_id):
        return self._members.get(member_id)


class FakeBot:
    def __init__(self, guild):
        self._guild = guild

    def get_guild(self, guild_id):
        return self._guild if guild_id == GUILD_ID else None


async def call(client, path, role_id, discord_id):
    return await client.post(
        f"/internal/tournaments/discord/{path}",
        json={"role_id": str(role_id), "discord_id": str(discord_id)},
        headers={"X-Service-Token": TOKEN},
    )


async def main():
    bot_top = FakeRole(900, "NiceBot", position=50)
    participant = FakeRole(11111, PARTICIPANT_ROLE_PREFIX + "cup", position=5)
    em_role = FakeRole(22222, "Eventmanagement", position=40)
    high_participant = FakeRole(
        33333, PARTICIPANT_ROLE_PREFIX + "hoch", position=99
    )
    member = FakeMember()
    guild = FakeGuild(
        roles=[participant, em_role, high_participant],
        members={55555: member},
        bot_top_role=bot_top,
    )
    app = create_service_app(
        {"TURNIER_SERVICE_TOKEN": TOKEN, "GUILD_ID": GUILD_ID}, FakeBot(guild)
    )

    failures = []

    def check(label, cond):
        print(("PASS  " if cond else "FAIL  ") + label)
        if not cond:
            failures.append(label)

    async with TestClient(TestServer(app)) as client:
        # 1) Nicht-Teilnehmer-Rolle (EM) → 403, kein add_roles
        res = await call(client, "role-assign", em_role.id, 55555)
        body = await res.json()
        check("assign EM-Rolle → 403", res.status == 403)
        check(
            "assign EM-Rolle → klare Meldung (Präfix)",
            PARTICIPANT_ROLE_PREFIX in body.get("error", ""),
        )
        check("assign EM-Rolle → KEIN add_roles", member.added == [])

        # 2) Nicht-Teilnehmer-Rolle bei remove → 403, kein remove_roles
        res = await call(client, "role-remove", em_role.id, 55555)
        check("remove EM-Rolle → 403", res.status == 403)
        check("remove EM-Rolle → KEIN remove_roles", member.removed == [])

        # 3) Teilnehmer-Rolle >= Bot-Top-Rolle → 403 trotz Präfix
        res = await call(client, "role-assign", high_participant.id, 55555)
        check("assign Rolle über Bot-Top → 403", res.status == 403)
        check("assign Rolle über Bot-Top → KEIN add_roles", member.added == [])

        # 4) Teilnehmer-Rolle → 200 + add_roles
        res = await call(client, "role-assign", participant.id, 55555)
        body = await res.json()
        check("assign Teilnehmer-Rolle → 200 ok", res.status == 200 and body.get("ok"))
        check("assign Teilnehmer-Rolle → add_roles", member.added == [participant])

        # 5) Teilnehmer-Rolle remove → 200 + remove_roles
        res = await call(client, "role-remove", participant.id, 55555)
        body = await res.json()
        check("remove Teilnehmer-Rolle → 200 ok", res.status == 200 and body.get("ok"))
        check("remove Teilnehmer-Rolle → remove_roles", member.removed == [participant])

        # 6) Unbekannte Rolle → 404
        res = await call(client, "role-assign", 99999, 55555)
        check("assign unbekannte Rolle → 404", res.status == 404)

    if failures:
        print(f"\n{len(failures)} Check(s) FEHLGESCHLAGEN")
        return 1
    print("\nAlle Checks PASS")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
