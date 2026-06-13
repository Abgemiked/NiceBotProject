"""Stub-Tests für die Turnier-Slash-Commands (Stage D).

Standalone (kein pytest in der venv): leichte Fakes für Interaction/Member,
aiohttp wird über einen Monkeypatch von turnier_common._get_json / request_deeplink
ersetzt. Geprüft:

  - Rollenprüfung (EM/Admin/Caster) gegen die Rollen-IDs des Members
  - /turnier-hilfe deckt rollenabhängig alle Befehle ab
  - Deeplink-Erzeugung übergibt den korrekten redirect_path
  - rollen-gated Commands → Forbidden-Meldung ohne Rolle, kein Deeplink-Call
  - /anmelden liefert Gating-Hinweis + Deeplink mit /t/:slug

Ausführen:  .venv\\Scripts\\python.exe test_turnier_cmds.py
(Windows-cp1252-Konsole: vorher  set PYTHONIOENCODING=utf-8)
"""
import asyncio
import sys

from commands.turnier_cmds import turnier_common as tc
from commands.turnier_cmds import teilnehmer_cmds as teil
from commands.turnier_cmds import admin_cmds as adm

EM_ROLE = tc.DEFAULT_EM_ROLE_ID
ADMIN_ROLE = tc.DEFAULT_ADMIN_ROLE_IDS[0]
CASTER_ROLE = tc.DEFAULT_CASTER_ROLE_ID

CFG = {"TURNIER_API_URL": "http://backend:3130", "TURNIER_SERVICE_TOKEN": "secret"}

_failures = []


def check(name, cond):
    if cond:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}")
        _failures.append(name)


class FakeRole:
    def __init__(self, role_id):
        self.id = role_id


class FakeMember:
    def __init__(self, role_ids=()):
        self.id = 424242424242
        self.name = "mike"
        self.roles = [FakeRole(r) for r in role_ids]


class FakeInteraction:
    """Fängt defer + edit_original_response ab."""

    def __init__(self, member):
        self.user = member
        self.deferred_ephemeral = None
        self.content = None
        self.embed = None

        outer = self

        class _Resp:
            async def defer(self, ephemeral=False):
                outer.deferred_ephemeral = ephemeral

        self.response = _Resp()

    async def edit_original_response(self, content=None, embed=None):
        self.content = content
        self.embed = embed


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------- Rollenprüfung

def test_role_checks():
    print("[Rollenprüfung]")
    em = FakeMember([EM_ROLE])
    admin = FakeMember([ADMIN_ROLE])
    caster = FakeMember([CASTER_ROLE])
    plain = FakeMember([])

    check("EM erkannt", tc.is_eventmanager(CFG, em))
    check("Admin zählt als EM-or-Admin", tc.is_em_or_admin(CFG, admin))
    check("Plain ist kein EM-or-Admin", not tc.is_em_or_admin(CFG, plain))
    check("Caster erkannt", tc.is_caster(CFG, caster))
    check("EM ist kein Caster", not tc.is_caster(CFG, em))
    # User ohne .roles (z.B. DM) darf nicht crashen
    check("User ohne roles → kein EM", not tc.is_em_or_admin(CFG, object()))


# ---------------------------------------------------------------- Hilfe-Coverage

def test_help_coverage():
    print("[/turnier-hilfe Coverage]")
    plain = build = teil.build_help_text(CFG, FakeMember([]))
    for cmd in ["/turnier-hilfe", "/turniere", "/turnier-info", "/anmelden", "/mein-team"]:
        check(f"Teilnehmer-Hilfe enthält {cmd}", cmd in plain)
    check("Teilnehmer sieht KEINE EM-Befehle", "/turnier-starten" not in plain)
    check("Teilnehmer sieht KEINE Caster-Befehle", "/caster-info" not in plain)

    em_help = teil.build_help_text(CFG, FakeMember([EM_ROLE]))
    for cmd in ["/turnier-erstellen", "/anmeldung-oeffnen", "/turnier-starten",
                "/ko-starten", "/turnier-beenden"]:
        check(f"EM-Hilfe enthält {cmd}", cmd in em_help)

    caster_help = teil.build_help_text(CFG, FakeMember([CASTER_ROLE]))
    check("Caster-Hilfe enthält /caster-info", "/caster-info" in caster_help)


# ---------------------------------------------------------------- Deeplink/redirect

def test_deeplink_redirect_path():
    print("[Deeplink redirect_path]")
    captured = {}

    async def fake_deeplink(base_url, token, discord_id, username, redirect_path=None):
        captured["redirect_path"] = redirect_path
        captured["discord_id"] = discord_id
        return f"https://turnier.abgemiked.de/verknuepfen/abc"

    async def fake_fetch_tournament(base_url, token, needle):
        return {"name": "Sommer Cup", "slug": "sommer-cup", "status": "registration",
                "team_count": 3, "max_teams": 8}

    orig_dl, orig_ft = tc.request_deeplink, tc.fetch_tournament
    teil.tc.request_deeplink = fake_deeplink
    teil.tc.fetch_tournament = fake_fetch_tournament
    try:
        inter = FakeInteraction(FakeMember([]))
        run(teil.anmelden_handler(CFG, inter, "Sommer Cup"))
        check("ephemeral defer", inter.deferred_ephemeral is True)
        check("redirect_path = /t/sommer-cup", captured.get("redirect_path") == "/t/sommer-cup")
        check("Gating-Hinweis (Discord+Twitch) im Text", "Discord" in inter.content and "Twitch" in inter.content)
        check("Deeplink-URL im Text", "verknuepfen/abc" in inter.content)
    finally:
        teil.tc.request_deeplink = orig_dl
        teil.tc.fetch_tournament = orig_ft


# ---------------------------------------------------------------- rollen-gated

def test_gated_commands():
    print("[rollen-gated Commands]")
    called = {"deeplink": 0}

    async def fake_deeplink(*a, **k):
        called["deeplink"] += 1
        return "https://turnier.abgemiked.de/verknuepfen/xyz"

    async def fake_fetch_tournament(base_url, token, needle):
        return {"name": "Cup", "slug": "cup", "status": "running",
                "team_count": 2, "max_teams": 8}

    orig_dl, orig_ft = tc.request_deeplink, tc.fetch_tournament
    adm.tc.request_deeplink = fake_deeplink
    adm.tc.fetch_tournament = fake_fetch_tournament
    try:
        # Ohne Rolle → Forbidden, KEIN Deeplink
        inter = FakeInteraction(FakeMember([]))
        run(adm.turnier_starten_handler(CFG, inter, "Cup"))
        check("ohne EM-Rolle → Forbidden", inter.content == adm.FORBIDDEN_EM)
        check("ohne Rolle: kein Deeplink-Call", called["deeplink"] == 0)

        # Mit EM-Rolle → Deeplink + Hinweis
        inter2 = FakeInteraction(FakeMember([EM_ROLE]))
        run(adm.turnier_starten_handler(CFG, inter2, "Cup"))
        check("mit EM-Rolle: Deeplink erzeugt", called["deeplink"] == 1)
        check("Start-Gate-Hinweis im Text", "Start-Gate" in inter2.content)

        # turnier-beenden Irreversibel-Hinweis
        inter3 = FakeInteraction(FakeMember([ADMIN_ROLE]))
        run(adm.turnier_beenden_handler(CFG, inter3, "Cup"))
        check("beenden: Irreversibel-Hinweis", "Irreversibel" in inter3.content)

        # caster-info ohne Caster-Rolle → Forbidden
        inter4 = FakeInteraction(FakeMember([EM_ROLE]))
        run(adm.caster_info_handler(CFG, inter4, "Cup"))
        check("caster-info ohne Caster-Rolle → Forbidden", inter4.content == adm.FORBIDDEN_CASTER)

        # caster-info mit Caster-Rolle → M6-Platzhalter
        inter5 = FakeInteraction(FakeMember([CASTER_ROLE]))
        run(adm.caster_info_handler(CFG, inter5, "Cup"))
        check("caster-info mit Rolle → M6-Hinweis", "M6" in inter5.content)
    finally:
        adm.tc.request_deeplink = orig_dl
        adm.tc.fetch_tournament = orig_ft


def main():
    asyncio.set_event_loop(asyncio.new_event_loop())
    test_role_checks()
    test_help_coverage()
    test_deeplink_redirect_path()
    test_gated_commands()
    print()
    if _failures:
        print(f"FEHLGESCHLAGEN: {len(_failures)} → {_failures}")
        sys.exit(1)
    print("ALLE TESTS GRÜN")


if __name__ == "__main__":
    main()
