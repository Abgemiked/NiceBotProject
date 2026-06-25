# PLAN M2 — nicebot-admin: Bot-Konfiguration verwalten

**Branch:** feat/admin-m2-config
**Review-Rat-Stufe:** 3 (Config-Schreibzugriff + Secrets/RBAC)
**FDS:** ~/.claude/results/nicebot/LASTENHEFT_web-verwaltung_v0.1.md (5.2)

## Tasks
- [x] T1: config_schema.py — Whitelist (EDITABLE_KEYS), Feld-Metadaten, Typ-Validierung, apply_updates (Fremd-Keys erhalten)
- [x] T2: bot_config.py — read/atomic write (tempfile + os.replace + fsync) der gemounteten config.json
- [x] T3: authz.py — current_tier_live() (frische Rollenprüfung gegen Bot-API)
- [x] T4: routes/config_routes.py — GET /api/config (maskiert), PUT /api/config (re-validate live tier, Whitelist, atomar)
- [x] T5: main.py — Router registriert; config.py — BOT_CONFIG_PATH
- [x] T6: Frontend — api.ts (fetchConfig/saveConfig), ConfigPage.tsx, App.tsx eingebunden
- [x] T7: Tests test_config.py

## Sicherheits-Designentscheidungen
- Secrets (TOKEN, TURNIER_SERVICE_TOKEN) NICHT in EDITABLE_KEYS → Schreibversuch → 403 (PermissionError).
- DC-Mod darf Nicht-Secrets schreiben; Schreib-Tier wird FRISCH gegen Bot-API geprüft (nicht aus Session).
- Path-Traversal unmöglich: Key-Namen werden nie als Pfad genutzt; Pfad fix aus ENV.
- Atomar: Bot sieht nie halbe Datei; Nicht-Whitelist-Keys (inkl. Secrets/Turnier) bleiben erhalten.

## Tests
- test_config.py: Whitelist, Typvalidierung (id/idlist/string/hostlist), Secret-Write→PermissionError,
  can_write=False→PermissionError, apply_updates erhält Fremd-Keys, atomarer Roundtrip ohne Temp-Reste.
- **Ergebnis: 22/22 grün** (10 RBAC + 12 Config), 2026-06-25. Backend py_compile OK.

## Review-Rat (Stufe 3)
- 6/6 Sonnet PASS (Schreib-Autorisierung, Validierung, atomares Schreiben, Pfad/IO, Secret-Maskierung, Frontend).
- Gehärtet: kaputte config.json → BotConfigError→503 (kein 500-Leak); 3 Negativtests ergänzt; Frontend nutzt restart_required_keys.
- **Opus-Audit: BESTÄTIGT** — fail-closed-Schreibkette vollständig, Secret-Schutz doppelt, Fremd-Keys erhalten.
- Tests: 25/25 grün (10 RBAC + 15 Config).

## Known Limitations (M2)
- Lost-Update bei gleichzeitigen PUTs (read-modify-write ohne Lock): letzter gewinnt. Kein Korruptionsrisiko
  (Schreiben bleibt atomar). Bei mehr Parallel-Admins später Datei-Lock erwägen.
- Kein expliziter Body-Größenlimit (Auth-geschützt; ggf. NPM client_max_body_size).

## Deploy
- main 733df9a → /opt/nicebot, docker compose build/up nicebot-admin. Frontend-Build sauber (vite ✓).
- Verifiziert: /api/health=ok; /api/config ohne Session=401; interner Live-Lesetest: config.json gelesen (17 Felder),
  TOKEN für DC-Mod maskiert. UI-Edit-Test offen → User-Abnahme.
