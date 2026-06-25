# nicebot — Discord-Bot (Abgemiked Media)

## Session-Start-Pflicht

Bei jedem Session-Start in diesem Verzeichnis:

1. Lies die Anforderungsdatei: `~/.claude/skills/project-requirements/nicebot.md`
2. Projektbezogene Anfragen laufen über den PM-Skill (`project-manager`) — nicht selbst analysieren/implementieren.
3. PM-Memory: `~/.claude/results/nicebot/projektmanager-memory.md`

## Kurzüberblick

- **Stack:** Python 3, discord.py 2.7.1, SQLite, Docker
- **Funktion:** Discord-Bot mit Level-System, Channel-Filtern (GIF/Bild/Bot/Spam), Voice-Temp-Channels, Turnier-System, Streamer-Verwaltung, Logging, Statistiken
- **Geplant:** Web-Verwaltungstool unter `nicebot.abgemiked.de` (Discord-OAuth, Rollen-RBAC)
- **Sprache:** durchgängig Deutsch

## Verboten

- Kein `git push` auf main ohne Review
- Keine Discord-Token / Credentials committen (`.env`, `config.json` bleiben lokal)
- Keine Produktionsdaten (SQLite-DB, Logs) löschen
