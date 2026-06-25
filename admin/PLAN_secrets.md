# PLAN — Secrets-Verwaltung (.env, Voll-Admin)

**Branch:** feat/admin-secrets
**Review-Rat-Stufe:** 3 (Lesen/Schreiben von Laufzeit-Secrets)
**Auslöser:** User — Secrets voll einsehbar+änderbar, standardmäßig verborgen (Augen-Toggle je Feld).

## Tasks
- [x] docker-compose: Bot-.env rw in Admin gemountet (./.env:/app/bot_env/.env)
- [x] config.py: BOT_ENV_PATH
- [x] env_secrets.py: read_secrets/write_secrets — Whitelist {NICEBOT_TOKEN, TURNIER_SERVICE_TOKEN}, atomar (tempfile+fsync+os.replace), Fremd-Zeilen/Kommentare erhalten, leere Werte abgelehnt
- [x] routes/secrets_routes.py: GET/PUT /api/secrets — NUR FULL_ADMIN (live gegen Bot-API), DC-Mod/none 403; PUT loggt Audit (nur Key-Namen, keine Werte) + restart_required
- [x] main.py: Router registriert
- [x] config_routes: config.json-Secrets aus der Konfig-Anzeige ENTFERNT (Secrets jetzt eigener Tab) → kein irreführendes Leerfeld mehr
- [x] Frontend: SecretsPage.tsx (Passwort-Felder + Augen-Toggle je Secret, Save, Neustart-Hinweis); api.ts fetchSecrets/saveSecrets; App-Route /secrets + Nav-Tab NUR Voll-Admin
- [x] Tests test_secrets.py

## Sicherheit
- GET liefert Klartext NUR an live-geprüften FULL_ADMIN; DC-Mod sieht den Tab nicht und bekommt 403.
- Schreiben: Whitelist (keine beliebigen .env-Keys), kein Path-Traversal (Pfad fix aus ENV), atomar, Fremd-Keys/Kommentare bleiben.
- Audit protokolliert nur, WELCHE Keys geändert wurden — nie die Werte.
- Erweiterte Angriffsfläche bewusst akzeptiert (User-Entscheidung): Bot-.env im Admin-Container lesbar/schreibbar.
- Bot übernimmt geänderte .env erst nach Neustart (UI-Hinweis); Admin löst KEINEN Neustart selbst aus (kein docker-socket).

## Tests
- test_secrets.py: read Whitelist, write+preserve, reject non-whitelist/empty/no-change, append missing, missing file → unset. **54/54 grün gesamt.**

## Review-Rat (Stufe 3)
- 5/5 Sonnet PASS. Gehärtet: Newline-Injection abgelehnt; Schreiben IN-PLACE (Single-File-Bind-Mount; os.replace würde Inode entkoppeln).
- Opus-Audit: BESTÄTIGT. In-Place-Truncate-Restrisiko gering/akzeptabel (winzige Datei, mount-bedingt).
- Tests: 55/55 grün.

## Deploy
- Nur nicebot-admin (Bot unverändert; compose-Volume ./.env:/app/bot_env/.env neu → up -d recreate).
