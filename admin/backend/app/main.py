"""nicebot-admin — FastAPI-App (M1: Infra & Auth-Gerüst).

Serviert die gebaute React-SPA als statische Dateien und stellt die API unter
/api/* bereit. Reverse Proxy (NPM) terminiert TLS; dieser Service hört nur
intern im Docker-Netz (kein Host-Port-Mapping).
"""
import os

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import settings

# Security-Header für alle Antworten (M8-Härtung).
_SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; img-src 'self' data:; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; "
        "form-action 'self' https://discord.com"
    ),
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
}
# Methoden, die einen CSRF-Origin-Check brauchen.
_STATE_METHODS = {"POST", "PUT", "DELETE", "PATCH"}
from .routes import (
    audit_routes,
    auth_routes,
    config_routes,
    discord_routes,
    level_routes,
    member_routes,
    me_routes,
    secrets_routes,
    streamer_routes,
)

app = FastAPI(title="nicebot-admin", version="0.1.0")


@app.middleware("http")
async def security_and_csrf(request: Request, call_next):
    # CSRF: zustandsändernde /api-Requests müssen vom eigenen Origin kommen.
    if request.method in _STATE_METHODS and request.url.path.startswith("/api/"):
        allowed = settings.public_origin()
        origin = request.headers.get("origin")
        referer = request.headers.get("referer") or ""
        ok = bool(allowed) and (
            origin == allowed or referer == allowed or referer.startswith(allowed + "/")
        )
        if not ok:
            return JSONResponse({"detail": "CSRF: ungültige Herkunft"}, status_code=403)
    response = await call_next(request)
    for k, v in _SECURITY_HEADERS.items():
        response.headers.setdefault(k, v)
    return response


app.include_router(auth_routes.router)
app.include_router(me_routes.router)
app.include_router(config_routes.router)
app.include_router(level_routes.router)
app.include_router(audit_routes.router)
app.include_router(discord_routes.router)
app.include_router(secrets_routes.router)
app.include_router(streamer_routes.router)
app.include_router(member_routes.router)

# Pfad zur gebauten Frontend-SPA (im Docker-Image kopiert; lokal optional).
FRONTEND_DIST = os.environ.get("FRONTEND_DIST", "/app/frontend_dist")


@app.get("/api/health")
def health():
    """Health-Check inkl. Hinweis auf fehlende Pflicht-Konfiguration."""
    missing = settings.missing_required()
    return JSONResponse(
        {"status": "ok" if not missing else "degraded", "missing_config": missing},
        status_code=200 if not missing else 503,
    )


if os.path.isdir(FRONTEND_DIST):
    assets_dir = os.path.join(FRONTEND_DIST, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        """SPA-Fallback: alle Nicht-/api-Routen liefern index.html."""
        index = os.path.join(FRONTEND_DIST, "index.html")
        candidate = os.path.join(FRONTEND_DIST, full_path)
        if full_path and os.path.isfile(candidate):
            return FileResponse(candidate)
        return FileResponse(index)
