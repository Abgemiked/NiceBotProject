"""FastAPI-Dependencies für Auth & RBAC."""
from fastapi import Depends, HTTPException, Request, status

from .config import settings
from .rbac import Tier
from .session import read_session


def current_user(request: Request):
    """Liest die signierte Session-Cookie. 401, wenn nicht eingeloggt/abgelaufen."""
    token = request.cookies.get(settings.SESSION_COOKIE)
    data = read_session(token)
    if not data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Nicht angemeldet")
    return data


def require_access(user=Depends(current_user)):
    """Verlangt mindestens DC-Mod. NONE → 403 (gehört keiner erlaubten Rolle an)."""
    tier = Tier(user.get("tier", Tier.NONE.value))
    if tier == Tier.NONE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Kein Zugriff")
    return user


def require_full_admin(user=Depends(require_access)):
    """Verlangt FULL_ADMIN (für Secret-Operationen)."""
    if Tier(user.get("tier", Tier.NONE.value)) != Tier.FULL_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Nur Voll-Admin")
    return user
