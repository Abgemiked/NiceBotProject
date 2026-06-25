"""Geschützte Demo-/Identitäts-Endpunkte (M1)."""
from fastapi import APIRouter, Depends

from ..deps import require_access
from ..rbac import Tier, permissions_for

router = APIRouter(prefix="/api", tags=["me"])


@router.get("/me")
def me(user=Depends(require_access)):
    """Liefert die eigene Identität + Rechte fürs rollenabhängige Frontend."""
    tier = Tier(user.get("tier"))
    return {
        "discord_id": user.get("discord_id"),
        "username": user.get("username"),
        "permissions": permissions_for(tier),
    }
