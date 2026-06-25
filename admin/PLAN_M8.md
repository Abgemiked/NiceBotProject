# PLAN M8 — DSGVO & Härtung

**Review-Rat-Stufe:** 3 (Security-Middleware + Datenschutz)
**Basis:** DSGVO-Gutachten + Security-Audit (team-legal/team-audit-Perspektive)

## Umgesetzte Härtung
- [x] CSRF: Origin/Referer-Check-Middleware für POST/PUT/DELETE/PATCH auf /api (fail-closed bei leerer Origin-Config)
- [x] Session-Cookie SameSite=strict (State-Cookie bleibt lax → OAuth-Redirect intakt)
- [x] Security-Header: CSP (frame-ancestors 'none', script/connect 'self'), X-Frame-Options DENY, nosniff, Referrer-Policy, HSTS
- [x] DSGVO Speicherbegrenzung: Audit-Log Aufbewahrungsfrist (AUDIT_RETENTION_DAYS=60) + täglicher Auto-Purge (purge_old)
- [x] DSGVO Datenminimierung: AUDIT_STORE_CONTENT (Default an) — Inhaltsspeicherung abschaltbar
- [x] config/level PUT bereits live-Tier-geprüft (Audit-Finding #2 war bereits erfüllt)

## Review-Rat (Stufe 3)
- 4/4 Sonnet PASS (CSRF-Middleware, CSP/Header, Audit-Retention, Regression) + Opus BESTÄTIGT.
- Origin-Header nicht browser-spoofbar → CSRF wirksam; CSP bricht SPA nicht; Login/Betrieb intakt; Auto-Purge wirksam.
- Watch-item (kein Blocker): img-src 'self' data: würde externe Discord-Avatare blocken (aktuell keine View mit Avataren).

## Offen / Deliverables (User-Aktion)
- Datenschutzhinweis im Discord veröffentlichen (Entwurf wird geliefert) — Verantwortlicher, Zwecke, Speicherdauer, Betroffenenrechte.
- Optional: Verarbeitungsverzeichnis (Art. 30). Finale anwaltliche Prüfung empfohlen.
- Betroffenenrechte (Auskunft/Löschung) sind via Admin-Tool teilweise abbildbar (Level/Audit), formaler Prozess offen.

## Deploy
- (nach PASS) Deploy BEIDE Container.
