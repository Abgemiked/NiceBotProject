"""Smoke-/Logik-Test für die globale Teamleader-Rolle (Stage B.1).

Standalone (kein pytest in der venv): aiohttp-TestClient gegen die echte
create_service_app, Bot/Guild/Member sind leichte Fakes. Geprüft:

  - assign ohne vorhandene Rolle  → ensure-create legt "Teamleader" an, add_roles
  - assign mit vorhandener Rolle  → wiederverwendet (kein zweites create_role)
  - remove                        → remove_roles
  - unbekannter Member            → 404, kein add_roles
  - falscher/fehlender Token      → 401
  - Rolle >= Bot-Top-Rolle        → 403, kein add_roles
  - Kategorie-Positionierung      → Anker per Name aufgelöst (mit/ohne Umlaut)

Ausführen:  .venv\\Scripts\\python.exe test_service_api_teamleader.py
(Windows-cp1252-Konsole: vorher  set PYTHONIOENCODING=utf-8)
"""
import asyncio
import sys

from aiohttp.test_utils import TestClient, TestServer

from service_api import (
    TEAMLEADER_ROLE_NAME,
    _resolve_anchor_categories,
    create_service_app,
)

TOKEN = "test-secret"
GUILD_ID = 123


class _FakeResp:
    """Minimaler Stub für discord.NotFound (erwartet ein Response-Objekt)."""
    status = 404
    reason = "Not Found"


class FakeRole:
    def __init__(self, role_id, name, position):
        self.id = role_id
        self.name = name
        self.position = position

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


class FakeCategory:
    def __init__(self, name):
        self.name = name


class FakeGuild:
    def __init__(self, roles, members, bot_top_role, categories=None):
        self._roles = list(roles)
        self._members = members
        self.me = FakeMember(top_role=bot_top_role)
        self.categories = categories or []
        self.create_calls = 0
        self._next_id = 80000

    @property
    def roles(self):
        return self._roles

    def get_role(self, role_id):
        for r in self._roles:
            if r.id == role_id:
                return r
        return None

    def get_member(self, member_id):
        return self._members.get(member_id)

    async def fetch_member(self, member_id):
        m = self._members.get(member_id)
        if m is None:
            import discord
            raise discord.NotFound(_FakeResp(), "unknown member")
        return m

    async def create_role(self, name, mentionable=False, hoist=False,
                          permissions=None, reason=None):
        self.create_calls += 1
        role = FakeRole(self._next_id, name, position=10)
        self._next_id += 1
        self._roles.append(role)
        return role


class FakeBot:
    def __init__(self, guild):
        self._guild = guild

    def get_guild(self, guild_id):
        return self._guild if guild_id == GUILD_ID else None


def make_app(guild):
    return create_service_app(
        {"TURNIER_SERVICE_TOKEN": TOKEN, "GUILD_ID": GUILD_ID}, FakeBot(guild)
    )


async def call(client, path, discord_id, token=TOKEN):
    headers = {"X-Service-Token": token} if token is not None else {}
    return await client.post(
        f"/internal/teamleader-role/{path}",
        json={"discord_id": str(discord_id)},
        headers=headers,
    )


async def main():
    failures = []

    def check(label, cond):
        print(("PASS  " if cond else "FAIL  ") + label)
        if not cond:
            failures.append(label)

    bot_top = FakeRole(900, "NiceBot", position=50)

    # --- Szenario 1: keine Teamleader-Rolle vorhanden → ensure-create ---------
    member = FakeMember()
    guild = FakeGuild(roles=[], members={55555: member}, bot_top_role=bot_top)
    async with TestClient(TestServer(make_app(guild))) as client:
        res = await call(client, "assign", 55555)
        body = await res.json()
        check("assign ohne Rolle → 200", res.status == 200 and body.get("ok"))
        check("ensure-create: Rolle 'Teamleader' angelegt", guild.create_calls == 1)
        check("add_roles ausgeführt", len(member.added) == 1)
        check(
            "angelegte Rolle hat exakt den Namen",
            member.added and member.added[0].name == TEAMLEADER_ROLE_NAME,
        )

        # zweiter assign → Rolle wiederverwenden, KEIN zweites create_role
        res = await call(client, "assign", 55555)
        check("zweiter assign → kein erneutes create_role", guild.create_calls == 1)

        # remove → remove_roles
        res = await call(client, "remove", 55555)
        body = await res.json()
        check("remove → 200", res.status == 200 and body.get("ok"))
        check("remove_roles ausgeführt", len(member.removed) == 1)

        # unbekannter Member → 404, kein add
        before = len(member.added)
        res = await call(client, "assign", 66666)
        check("unbekannter Member → 404", res.status == 404)
        check("unbekannter Member → kein add_roles", len(member.added) == before)

        # falscher Token → 401
        res = await call(client, "assign", 55555, token="falsch")
        check("falscher Token → 401", res.status == 401)

    # --- Szenario 2: Teamleader-Rolle existiert bereits, aber >= Bot-Top ------
    existing = FakeRole(7777, TEAMLEADER_ROLE_NAME, position=99)
    member2 = FakeMember()
    guild2 = FakeGuild(roles=[existing], members={55555: member2}, bot_top_role=bot_top)
    async with TestClient(TestServer(make_app(guild2))) as client:
        res = await call(client, "assign", 55555)
        check("Rolle über Bot-Top → 403", res.status == 403)
        check("Rolle über Bot-Top → kein add_roles", member2.added == [])
        check("Rolle über Bot-Top → kein create_role", guild2.create_calls == 0)

    # --- Szenario 3: Anker-Kategorie-Auflösung (mit/ohne Umlaut) --------------
    cats = [
        FakeCategory("Allgemein"),
        FakeCategory("ÖFFENTLICH"),
        FakeCategory("Temporare Channel"),
    ]
    g3 = FakeGuild(roles=[], members={}, bot_top_role=bot_top, categories=cats)
    public_cat, temp_cat = _resolve_anchor_categories(g3)
    check("Anker: 'Öffentlich' case-insensitive gefunden", public_cat is cats[1])
    check("Anker: 'Temporäre Channel' ohne Umlaut gefunden", temp_cat is cats[2])

    # kein Anker vorhanden → beide None (Default-Position bleibt)
    g4 = FakeGuild(roles=[], members={}, bot_top_role=bot_top,
                   categories=[FakeCategory("Sonst")])
    p4, t4 = _resolve_anchor_categories(g4)
    check("Anker fehlt → beide None", p4 is None and t4 is None)

    if failures:
        print(f"\n{len(failures)} Check(s) FEHLGESCHLAGEN")
        return 1
    print("\nAlle Checks PASS")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
