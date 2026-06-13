"""Smoke-/Logik-Test für den DM-Endpoint /internal/dm (Batch 3, Nachtrag 4).

Standalone (kein pytest in der venv): aiohttp-TestClient gegen die echte
create_service_app, Bot/Guild/Member sind leichte Fakes. Geprüft:

  - DM zugestellt              → 200 {"ok": true, "delivered": true}
  - allowed_mentions=none      → der User-Text pingt niemals
  - User hat DMs zu (Forbidden)→ 200 {"ok": true, "delivered": false} (tolerant)
  - unbekannter Member         → 200 {"ok": true, "delivered": false} (tolerant)
  - falscher/fehlender Token   → 401, keine Zustellung
  - fehlende message           → 400
  - ungültige discord_id       → 400

Ausführen:  python test_service_api_dm.py
(Windows-cp1252-Konsole: vorher  set PYTHONIOENCODING=utf-8)
"""
import asyncio
import sys

import discord
from aiohttp.test_utils import TestClient, TestServer

from service_api import create_service_app

TOKEN = "test-secret"
GUILD_ID = 123


class _FakeResp:
    status = 404
    reason = "Not Found"


class FakeMember:
    def __init__(self, dm_blocked=False):
        self.dm_blocked = dm_blocked
        self.sent = []  # (message, allowed_mentions)

    async def send(self, message, allowed_mentions=None):
        if self.dm_blocked:
            raise discord.Forbidden(_FakeResp(), "cannot send messages to this user")
        self.sent.append((message, allowed_mentions))


class FakeGuild:
    def __init__(self, members):
        self._members = members

    def get_member(self, member_id):
        return self._members.get(member_id)

    async def fetch_member(self, member_id):
        m = self._members.get(member_id)
        if m is None:
            raise discord.NotFound(_FakeResp(), "unknown member")
        return m


class FakeBot:
    def __init__(self, guild):
        self._guild = guild

    def get_guild(self, guild_id):
        return self._guild if guild_id == GUILD_ID else None


def make_app(guild):
    return create_service_app(
        {"TURNIER_SERVICE_TOKEN": TOKEN, "GUILD_ID": GUILD_ID}, FakeBot(guild)
    )


async def dm(client, discord_id, message="Hallo", token=TOKEN, omit_message=False):
    headers = {"X-Service-Token": token} if token is not None else {}
    body = {"discord_id": str(discord_id)}
    if not omit_message:
        body["message"] = message
    return await client.post("/internal/dm", json=body, headers=headers)


async def main():
    failures = []

    def check(label, cond):
        print(("PASS  " if cond else "FAIL  ") + label)
        if not cond:
            failures.append(label)

    # gültige Snowflakes (5–25 Stellen)
    OK_ID = 111000111000
    BLOCKED_ID = 222000222000
    UNKNOWN_ID = 999000999000
    member = FakeMember()
    blocked = FakeMember(dm_blocked=True)
    guild = FakeGuild(members={OK_ID: member, BLOCKED_ID: blocked})

    async with TestClient(TestServer(make_app(guild))) as client:
        # DM zugestellt
        res = await dm(client, OK_ID, message="@everyone Beitritts-Anfrage")
        body = await res.json()
        check("DM zugestellt → 200 delivered=true",
              res.status == 200 and body.get("ok") and body.get("delivered") is True)
        check("send wurde aufgerufen", len(member.sent) == 1)
        check(
            "allowed_mentions=none gesetzt (kein Ping durch User-Text)",
            member.sent and member.sent[0][1] is not None
            and member.sent[0][1].everyone is False,
        )

        # User hat DMs zu → tolerant delivered=false
        res = await dm(client, BLOCKED_ID)
        body = await res.json()
        check("DMs zu (Forbidden) → 200 delivered=false",
              res.status == 200 and body.get("ok") and body.get("delivered") is False)

        # unbekannter Member → tolerant delivered=false
        res = await dm(client, UNKNOWN_ID)
        body = await res.json()
        check("unbekannter Member → 200 delivered=false",
              res.status == 200 and body.get("delivered") is False)

        # falscher Token → 401, keine Zustellung
        before = len(member.sent)
        res = await dm(client, OK_ID, token="falsch")
        check("falscher Token → 401", res.status == 401)
        check("falscher Token → keine Zustellung", len(member.sent) == before)

        # fehlende message → 400
        res = await dm(client, OK_ID, omit_message=True)
        check("fehlende message → 400", res.status == 400)

        # ungültige discord_id → 400
        res = await client.post(
            "/internal/dm",
            json={"discord_id": "abc", "message": "x"},
            headers={"X-Service-Token": TOKEN},
        )
        check("ungültige discord_id → 400", res.status == 400)

    if failures:
        print(f"\n{len(failures)} Check(s) FEHLGESCHLAGEN")
        return 1
    print("\nAlle Checks PASS")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
