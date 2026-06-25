# PLAN — Admin UX: Routing + Konfig-Redesign + Channel/Rollen-Dropdowns

**Branch:** feat/admin-ux-routing
**Review-Rat-Stufe:** 3 (Bot-Endpoints + Config + Auth)
**Auslöser:** User-Feedback (kein One-Page → echte Routen; Konfig-Design; Channel/Rollen-Auswahl statt ID-Eingabe)

## Tasks
- [x] Bot: service_api.py — /internal/channels + /internal/roles (read-only, Token-Auth) + Registrierung
- [x] Admin: bot_client.fetch_channels/fetch_roles (+ _get_json-Helper); routes/discord_routes.py (GET /api/discord/channels, /roles); main.py registriert
- [x] Admin: config_schema FIELDS um "kind" (channel/voice/category/role/keyword/hostlist/idlist) erweitert
- [x] Frontend: react-router-dom — echte Routen /konfiguration, /level, /logs; Layout mit NavLink; Reload bleibt auf Route; Login-Guard
- [x] Frontend: ConfigPage neu — Gruppen-Tabs (Channels/Filter/Rollen/Secrets), aufgeräumte Karten-Optik
- [x] Frontend: Channel/Rollen/Kategorie-Felder als Dropdown aus echten Guild-Daten (Fallback Texteingabe, wenn Bot weg)
- [x] api.ts: fetchChannels/fetchRoles + DiscordChannel/DiscordRole + ConfigField.kind

## Sicherheit / Robustheit
- Neue Bot-Endpoints read-only, Token-geschützt (X-Service-Token), Guild-None → 503.
- Admin /api/discord/* hinter require_access; Bot-Fehler → 502, Frontend fällt auf Texteingabe zurück (kein Blocker).
- Save-Logik unverändert (nur geänderte editierbare Felder; Secrets nicht editierbar; Backend-Whitelist + Re-Validate live bleiben).
- SPA-Fallback (main.py) liefert index.html für /konfiguration|/level|/logs → Deep-Links + Reload funktionieren.

## Tests
- Backend unverändert grün (44/44). Bot/Admin py_compile OK. Frontend-Typecheck via Docker-Build (tsc -b).

## Review-Rat (Stufe 3)
- 6/6 Sonnet PASS (Bot-Endpoints, Admin-Auth, Routing/Build, Config-Redesign, Save-Regression, Konsistenz).
- Opus-Audit: BESTÄTIGT (Bot-Regression nein, Frontend-Build läuft durch, Config-Sicherheit unberührt).

## Deploy
- (nach PASS) Deploy BEIDE Container (nicebot: neue Endpoints; nicebot-admin: alles).
