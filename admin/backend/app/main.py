"""nicebot-admin — FastAPI-App (M1: Infra & Auth-Gerüst).

Serviert die gebaute React-SPA als statische Dateien und stellt die API unter
/api/* bereit. Reverse Proxy (NPM) terminiert TLS; dieser Service hört nur
intern im Docker-Netz (kein Host-Port-Mapping).
"""
import os

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .routes import audit_routes, auth_routes, config_routes, level_routes, me_routes

app = FastAPI(title="nicebot-admin", version="0.1.0")

app.include_router(auth_routes.router)
app.include_router(me_routes.router)
app.include_router(config_routes.router)
app.include_router(level_routes.router)
app.include_router(audit_routes.router)

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
