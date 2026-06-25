# PLAN M3 — nicebot-admin: Level-System & Ranglisten

**Branch:** feat/admin-m3-levels
**Review-Rat-Stufe:** 3 (Schreibzugriff auf Live-User-DB + RBAC)
**FDS:** ~/.claude/results/nicebot/LASTENHEFT_web-verwaltung_v0.1.md (5.3)

## Tasks
- [x] T1: config.py — LEVEL_DB_PATH (/app/bot_data/level_system.db)
- [x] T2: level_db.py — list_users (Suche/Sort-Whitelist/Pagination), get_user, update_user, validate_update; SQLite mit timeout, parametrisiert, LIKE-Escaping
- [x] T3: routes/level_routes.py — GET /api/levels, GET /api/levels/{id}, PUT /api/levels/{id} (nur FULL_ADMIN, live geprüft)
- [x] T4: main.py — Router registriert
- [x] T5: Frontend — api.ts (fetchLevels/updateLevel), LevelPage.tsx (Tabelle/Suche/Sort/Pagination/Edit-Modal), App.tsx Navigation
- [x] T6: tests/test_levels.py

## Sicherheits-Designentscheidungen
- ORDER BY nur aus Whitelist (SORT_COLUMNS) — kein roher Userinput → SQL-Injection-Schutz.
- Alle Queries parametrisiert; LIKE-Sonderzeichen escaped (kein Wildcard-Missbrauch).
- Schreiben nur FULL_ADMIN, Tier FRISCH gegen Bot-API (current_tier_live). DC-Mod read-only.
- Concurrency mit laufendem Bot: connect(timeout=5s), gezieltes UPDATE … WHERE user_id=?, sofort commit/close.
- exp/level-Grenzen (level 1..1000, exp 0..10_000_000), bool/non-int abgelehnt.
- Pagination geklammert (page>=1, page_size 1..100).

## Tests
- test_levels.py: normalize/Whitelist, Pagination, Suche (Name/ID), LIKE-Escaping, Injection-Sort ignoriert,
  get/update (Treffer/0), Validierung (Grenzen, bool/non-int). **37/37 grün gesamt** (10 RBAC + 15 Config + 12 Levels), 2026-06-25.

## Review-Rat (Stufe 3)
- 6/6 Sonnet PASS (2 nach Korrektur): SQL-Injection, RBAC, Concurrency, Validierung, Frontend, Datenexposition.
- Korrekturen: defensiver Guard fehlende discord_id→403; Frontend NaN/Leereingabe-Guard, Such-Race via applied-State, dynamisches colSpan.
- **Opus-Audit: BESTÄTIGT** — fail-closed-Kette vollständig, SQL-Injection ausgeschlossen, Concurrency unkritisch.
- Tests: 37/37 grün (10 RBAC + 15 Config + 12 Levels).

## Known Limitations (M3)
- Lost-Update: Admin setzt exp/level ABSOLUT; schreibt der Bot zwischen Anzeige und Save XP, geht dieses dazwischen.
  Für seltene manuelle FULL_ADMIN-Korrektur akzeptabel. Bei häufiger Nutzung: Read-Compare oder relative Delta-Updates.
- Empfehlung (Opus, → M5): Audit-Log der Admin-Overrides (wer/wann/alt→neu).

## Deploy
- main 5ca9e02 → /opt/nicebot, build/up nicebot-admin. Frontend-Build sauber.
- Verifiziert: /api/health=ok; /api/levels ohne Session=401; interner Live-Lesetest: 910 User, Top-3 nach Level gelesen.
- UI-Edit-Test (FULL_ADMIN) offen → User-Abnahme.
