# PLAN M6 (Streamer) + M7 (Member-Übersicht)

**Branch:** feat/admin-m6-m7
**Review-Rat-Stufe:** 3 (M6 = destruktive Discord-Writes: Channels/Rollen anlegen+löschen)

## Bot-Seite
- [x] commands/streamer/streamer_core.py — create_streamer/delete_streamer/list_streamers/streamer_exists (Permissions aus altem Code übernommen, _perms full/eingeschränkt)
- [x] streamer_cmd.py + delstreamer_cmd.py auf Core umgestellt (keine Duplikation, Slash-Commands erhalten)
- [x] service_api.py — GET/POST/DELETE /internal/streamers + GET /internal/guild-members (paginiert, Bots gefiltert, Suche), Token-Auth, Registrierung

## Admin-Seite
- [x] bot_client: _request (status,data), fetch_streamers/create_streamer/delete_streamer, fetch_members (search urlencoded)
- [x] deps.py: require_full_admin_live (geteilte Dependency, frische Bot-API-Tier-Prüfung)
- [x] routes/streamer_routes.py — GET (require_access), POST/DELETE (require_full_admin_live + Audit; 409/404-Mapping)
- [x] routes/member_routes.py — GET /api/members (require_access)
- [x] main.py: beide Router registriert
- [x] Frontend: StreamerPage (Liste; Anlegen/Löschen nur Voll-Admin, Lösch-Confirm), MemberPage (Tabelle/Suche/Pagination), App-Routen /streamer /mitglieder + Tabs, api.ts

## Sicherheit
- Streamer anlegen/löschen: NUR live-geprüftes FULL_ADMIN; jede Aktion im Audit (scope=streamer, action). Lösch-Bestätigung im UI.
- Bot-Endpoints Token-geschützt; Name validiert (1–50 Zeichen); create prüft Existenz → 409; delete 404 wenn fehlt.
- Member-Liste read-only, Bots gefiltert, paginiert (≤100), Suche serverseitig.
- Slash-Command-Regression vermieden (gemeinsames Core).

## Tests
- Backend bestehend 55/55 grün (admin-seitige M6/M7-Logik ist dünner Proxy; Kernlogik im Bot via Review geprüft, da discord-abhängig nicht lokal unit-testbar).

## Review-Rat (Stufe 3)
- 5/5 Sonnet PASS + Opus BESTÄTIGT. Autorisierung (FULL_ADMIN live) + Audit + enge Lösch-Schadensbegrenzung bestätigt.
- Known Limitation: create_streamer hat kein Rollback bei Teil-Anlage (Orphans möglich) — Cleanup-Pfad später.

## Deploy
- (nach PASS) Deploy BEIDE Container (Bot: Core+Endpoints; Admin: alles).
