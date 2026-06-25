# nicebot-admin — Web-Verwaltungstool

Web-Oberfläche zur Verwaltung des Discord-Bots `nicebot` unter
`nicebot.abgemiked.de`. Teil des Monorepos (eigener Container `nicebot-admin`).

> **Status:** M1 (Infra & Auth-Gerüst). Fachfunktionen (Konfiguration,
> Level-System, Logs, Audit-Log, Streamer, Member) folgen in M2–M8 laut FDS.

## Architektur
- **Backend:** FastAPI (`admin/backend`), serviert API unter `/api/*` und die
  gebaute React-SPA als statische Dateien.
- **Frontend:** React + TypeScript + Vite + Tailwind (`admin/frontend`).
- **Ein Container** (`nicebot-admin`), Multi-Stage-Build (Frontend → Backend-Image).
- **Auth:** Discord OAuth2 (Authorization Code Flow). Nach Login werden die
  Discord-Rollen über den bestehenden Bot-Endpunkt
  `GET http://nicebot:8130/internal/members/{id}/roles` (X-Service-Token) aufgelöst.
- **RBAC:**
  - **Voll-Admin** (Rollen `669879940296081420`, `1130018862990098463`): alles, inkl. Secrets.
  - **DC-Mod** (Rolle `1078399961496039515`): Einstellungen, **keine** Secrets.
  - sonst: kein Zugriff.

## Lokale Entwicklung
```bash
# Backend
cd admin/backend
python -m venv .venv && source .venv/bin/activate   # bzw. .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # Werte eintragen, COOKIE_SECURE=0 für http://localhost
uvicorn app.main:app --reload --port 8140

# Frontend (zweites Terminal)
cd admin/frontend
npm install
npm run dev        # Vite-Dev-Server, /api wird auf :8140 geproxyt

# Tests (RBAC-Logik)
cd admin/backend && python -m pytest
```

## Deployment (Hetzner, Docker + NPM + Cloudflare)
1. `admin/.env` auf dem Server anlegen (aus `.env.example`).
2. Build & Start:
   ```bash
   ssh hetzner "cd /opt/nicebot && git pull && docker compose build nicebot-admin && docker compose up -d nicebot-admin"
   ```
3. Health-Check: `docker compose logs nicebot-admin --tail=20` und intern
   `GET /api/health` (zeigt fehlende Pflicht-Config).

## Vom Betreiber bereitzustellen (externe Voraussetzungen)
| Was | Wo | Wert |
|---|---|---|
| **Discord-OAuth-App** | Discord Developer Portal | `DISCORD_CLIENT_ID`, `DISCORD_CLIENT_SECRET`; Redirect-URI `https://nicebot.abgemiked.de/api/auth/callback` |
| **Session-Secret** | `admin/.env` | `SESSION_SECRET` = `openssl rand -hex 32` |
| **Service-Token** | `admin/.env` | `BOT_SERVICE_TOKEN` = identisch zum `TURNIER_SERVICE_TOKEN` des Bots |
| **Guild-ID** | `admin/.env` | `GUILD_ID` der NiceCom-Guild |
| **Cloudflare DNS** | Cloudflare | A/CNAME-Record `nicebot.abgemiked.de` (proxied) → Server |
| **NPM Proxy-Host** | Nginx Proxy Manager | `nicebot.abgemiked.de` → `nicebot-admin:8140`, SSL aktiv |
