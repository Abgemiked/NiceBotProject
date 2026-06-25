# PLAN M1 — nicebot-admin: Infra & Auth-Gerüst

**Branch:** feat/admin-m1-auth
**Review-Rat-Stufe:** 3 (Auth/Secrets/RBAC)
**FDS:** ~/.claude/results/nicebot/LASTENHEFT_web-verwaltung_v0.1.md (M1)

## Architektur (abgestimmt)
- Backend FastAPI, Frontend React+TS+Vite+Tailwind.
- EIN Container `nicebot-admin` im Bot-Repo (Multi-Stage-Dockerfile: Frontend-Build → in Backend-Image kopiert, FastAPI serviert Static + API).
- Im npm-web-Netz, kein Host-Port-Mapping, kein eigener nginx/certbot.
- RBAC via Discord OAuth2 + Bot-Endpunkt `GET http://nicebot:8130/internal/members/{id}/roles`.

## Tasks
- [x] T1: Verzeichnisstruktur admin/backend + admin/frontend
- [x] T2: Backend config (ENV) + .env.example
- [x] T3: RBAC-Logik (Rollen-Mapping) + Tests
- [x] T4: Bot-API-Client (Rollenauflösung, X-Service-Token)
- [x] T5: Discord OAuth2 (login/callback/logout, State-CSRF, signierte Session-Cookie)
- [x] T6: Auth-Dependencies + /api/me + Secret-Maskierungs-Pattern
- [x] T7: FastAPI main + Static-Serving
- [x] T8: Frontend-Shell (Login + Dashboard, rollenabhängiges Rendering)
- [x] T9: Multi-Stage-Dockerfile + docker-compose-Service
- [x] T10: admin/README (Setup: Cloudflare/NPM/Discord-OAuth)

## Tests
- RBAC-Rollen-Mapping: tests/test_rbac.py — **10/10 grün** (2026-06-25)
- Backend py_compile: OK (alle Module)

## Review-Rat (Stufe 3)
- 6 Sonnet PASS (OAuth/CSRF, Session/Cookies, RBAC, Secret-Isolation, Infra/Docker, Fehlerpfade)
- 3 nicht-blockierende Hinweise gehärtet: leeres SESSION_SECRET → RuntimeError; require_full_admin sicherer Default; bot_client Nicht-JSON-Schutz.
- **Opus-Audit: BESTÄTIGT** — fail-closed durchgängig, AuthN/AuthZ getrennt (Rollen aus Bot-API als SSOT).
- Für M2 vorgemerkt: Tier wird in Session eingefroren → bei sensiblen Schreib-/Secret-Ops gegen Bot-API re-validieren.

## Offene externe Voraussetzungen (User liefert)
- Discord-OAuth-App: Client-ID + Secret, Redirect-URI https://nicebot.abgemiked.de/api/auth/callback
- Cloudflare DNS-Record nicebot.abgemiked.de
- NPM-Proxy-Host nicebot.abgemiked.de → nicebot-admin:8140
- TURNIER_SERVICE_TOKEN (Wert, identisch zum Bot)
