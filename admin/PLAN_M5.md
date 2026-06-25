# PLAN M5 (+M4) — Audit-Log-Persistenz & Statistiken

**Branch:** feat/admin-m5-audit
**Review-Rat-Stufe:** 3 (Produktiv-Bot-Änderung + neue Persistenz + PII)
**FDS:** ~/.claude/results/nicebot/LASTENHEFT_web-verwaltung_v0.1.md (5.4 + 5.6)

## Bot-Seite (neue Persistenz + Hooks — MUSS ausfallsicher sein)
- [x] audit_log.py (neu, top-level): init_db + log_event; ALLE Fehler geschluckt (Bot darf nie brechen). DB: /app/data/audit_log.db (neben Level-DB).
- [x] events/logs/delete_log.py: log_event("message_delete", target=Autor, channel, content) nach dem Channel-Post.
- [x] events/logs/leave_log.py: log_event("member_leave", target=Member) zuerst.
- [x] service_api.py: log_event("dm_sent") bei delivered; NEU /internal/stats (Membercount, X-Service-Token).
- [x] main.py: audit_log.init_db() beim Start.

## Admin-Seite
- [x] config.py: AUDIT_DB_PATH (/app/bot_data/audit_log.db).
- [x] audit_db.py: list_events (Filter event_type-Whitelist, Pagination, ORDER BY id DESC), log_admin_override; Schema idempotent.
- [x] bot_client.py: fetch_stats().
- [x] routes/audit_routes.py: GET /api/audit (require_access), GET /api/stats (via Bot-API).
- [x] level_routes.py: nach Level-Edit log_admin_override (alt→neu, Actor=eingeloggter Admin).
- [x] main.py: audit_router registriert.
- [x] Frontend: AuditPage.tsx (Statistik-Karten + Audit-Tabelle + Typ-Filter + Pagination), api.ts, App-Reiter "Logs".

## Sicherheits-Designentscheidungen
- Audit-Schreiben best effort: Bot-Hooks + Admin-Override fangen alle Exceptions → keine Funktionsstörung.
- list_events: event_type nur aus EVENT_TYPES-Whitelist; alle Queries parametrisiert.
- /api/audit + /api/stats hinter require_access (DC-Mod + Voll-Admin lesen; NONE 403).
- Bot↔Admin gleiches Schema (CREATE TABLE IF NOT EXISTS, identisch).
- PII: Audit speichert gelöschte Nachrichteninhalte + Usernamen → nur berechtigte Rollen; DSGVO-Aufbewahrung in M8.

## Tests
- test_audit.py: normalize/Filter-Whitelist, Pagination, list newest-first, override-Roundtrip, meta-JSON. **44/44 grün gesamt**, 2026-06-25.
- Bot audit_log.py: Smoke-Test (init+log+read) ok.

## Review-Rat (Stufe 3)
- 6/6 Sonnet PASS (1 nach Korrektur): Ausfallsicherheit, SQL, RBAC/PII, Frontend, Integration, Regression.
- Korrektur: AUDIT_DB_PATH explizit im Bot-Container (docker-compose) → deterministischer Pfad, Re-Review PASS.
- **Opus-Audit: BESTÄTIGT** — Bot-Hooks vollständig exception-gekapselt, Verhalten unverändert, Concurrency via timeout=5s.
- Tests: 44/44 grün.

## Deploy
- Deploy MUSS BEIDE Container neu bauen: nicebot (Bot-Hooks) + nicebot-admin. (nach PASS ausgefüllt)
