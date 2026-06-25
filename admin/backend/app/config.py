"""Konfiguration des nicebot-admin Backends.

Alle Werte kommen aus Umgebungsvariablen (Docker env / .env). Es werden
KEINE Secrets in den Code oder ins Repo geschrieben. Eine optionale .env wird
geladen, wenn python-dotenv verfügbar ist (lokale Entwicklung).
"""
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def _split_ids(raw):
    """Kommagetrennte Rollen-ID-Liste aus ENV → set[int]."""
    out = set()
    for part in (raw or "").replace(";", ",").split(","):
        part = part.strip()
        if part.isdigit():
            out.add(int(part))
    return out


class Settings:
    # --- Discord OAuth2 ---
    DISCORD_CLIENT_ID = os.environ.get("DISCORD_CLIENT_ID", "")
    DISCORD_CLIENT_SECRET = os.environ.get("DISCORD_CLIENT_SECRET", "")
    # Muss exakt der in der Discord-App hinterlegten Redirect-URI entsprechen.
    OAUTH_REDIRECT_URI = os.environ.get(
        "OAUTH_REDIRECT_URI", "https://nicebot.abgemiked.de/api/auth/callback"
    )
    DISCORD_API_BASE = "https://discord.com/api"

    # --- Session ---
    # Signaturschlüssel für Session- und State-Cookies. PFLICHT in Produktion.
    SESSION_SECRET = os.environ.get("SESSION_SECRET", "")
    SESSION_COOKIE = os.environ.get("SESSION_COOKIE", "nicebot_admin_session")
    SESSION_MAX_AGE = int(os.environ.get("SESSION_MAX_AGE", str(8 * 3600)))  # 8h
    # Hinter HTTPS (Cloudflare/NPM) → Secure-Cookies. Lokal via COOKIE_SECURE=0 abschaltbar.
    COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "1") not in ("0", "false", "False")

    # --- Bot Service-API (Rollenauflösung) ---
    BOT_API_URL = os.environ.get("BOT_API_URL", "http://nicebot:8130")
    # Identisch zum TURNIER_SERVICE_TOKEN des Bots (X-Service-Token).
    BOT_SERVICE_TOKEN = os.environ.get("BOT_SERVICE_TOKEN", "")
    GUILD_ID = os.environ.get("GUILD_ID", "")

    # --- RBAC: Rollen-IDs ---
    # Voll-Admin (inkl. Secrets). Default = vom User vorgegebene NiceCom-Rollen.
    FULL_ADMIN_ROLE_IDS = _split_ids(
        os.environ.get("FULL_ADMIN_ROLE_IDS", "669879940296081420,1130018862990098463")
    )
    # DC-Mod (Einstellungen, KEINE Secrets).
    MOD_ROLE_IDS = _split_ids(os.environ.get("MOD_ROLE_IDS", "1078399961496039515"))

    @classmethod
    def missing_required(cls):
        """Liste fehlender Pflicht-Settings (für Health/Startup-Check)."""
        required = {
            "DISCORD_CLIENT_ID": cls.DISCORD_CLIENT_ID,
            "DISCORD_CLIENT_SECRET": cls.DISCORD_CLIENT_SECRET,
            "SESSION_SECRET": cls.SESSION_SECRET,
            "BOT_SERVICE_TOKEN": cls.BOT_SERVICE_TOKEN,
        }
        return [k for k, v in required.items() if not v]


settings = Settings()
