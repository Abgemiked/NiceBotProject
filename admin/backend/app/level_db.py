"""Zugriff auf die Level-SQLite des Bots (M3).

Der Bot schreibt parallel (XP pro Nachricht), daher: kurze Verbindungen mit
Timeout, ausschließlich parametrisierte Queries, gezielte UPDATE … WHERE
user_id=?. Sortier-Spalten/Richtung kommen NUR aus einer Whitelist (niemals
roher Userinput im ORDER BY → SQL-Injection-Schutz).
"""
import sqlite3

from .config import settings

# Erlaubte Sortier-Spalten (Whitelist). Schlüssel = API-Wert, Wert = SQL-Spalte.
SORT_COLUMNS = {
    "level": "level",
    "exp": "exp",
    "username": "username",
    "user_id": "user_id",
}

PAGE_SIZE_MAX = 100
LEVEL_MIN, LEVEL_MAX = 1, 1000
EXP_MIN, EXP_MAX = 0, 10_000_000


class LevelValidationError(ValueError):
    pass


def _connect():
    conn = sqlite3.connect(settings.LEVEL_DB_PATH, timeout=5.0)
    conn.row_factory = sqlite3.Row
    return conn


def _row(r):
    return {"user_id": str(r["user_id"]), "exp": r["exp"], "level": r["level"],
            "username": r["username"]}


def normalize_list_params(sort="level", direction="desc", page=1, page_size=25):
    """Validiert/normalisiert Listen-Parameter rein (testbar, ohne DB)."""
    sql_col = SORT_COLUMNS.get(str(sort), "level")
    sql_dir = "ASC" if str(direction).lower() == "asc" else "DESC"
    try:
        page = max(1, int(page))
    except (TypeError, ValueError):
        page = 1
    try:
        page_size = int(page_size)
    except (TypeError, ValueError):
        page_size = 25
    page_size = min(PAGE_SIZE_MAX, max(1, page_size))
    return sql_col, sql_dir, page, page_size


def _where(search):
    """Baut WHERE-Klausel + params aus dem Suchbegriff (parametrisiert)."""
    if not search:
        return "", []
    s = str(search).strip()
    if not s:
        return "", []
    if s.isdigit():
        return "WHERE user_id = ?", [int(s)]
    return "WHERE username LIKE ? ESCAPE '\\'", ["%" + _escape_like(s) + "%"]


def _escape_like(s):
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def list_users(search=None, sort="level", direction="desc", page=1, page_size=25):
    sql_col, sql_dir, page, page_size = normalize_list_params(sort, direction, page, page_size)
    where, params = _where(search)
    offset = (page - 1) * page_size
    conn = _connect()
    try:
        total = conn.execute(f"SELECT COUNT(*) AS c FROM users {where}", params).fetchone()["c"]
        # sql_col/sql_dir stammen aus Whitelist → sichere Interpolation.
        rows = conn.execute(
            f"SELECT user_id, exp, level, username FROM users {where} "
            f"ORDER BY {sql_col} {sql_dir}, user_id ASC LIMIT ? OFFSET ?",
            params + [page_size, offset],
        ).fetchall()
    finally:
        conn.close()
    return {
        "items": [_row(r) for r in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def get_user(user_id):
    conn = _connect()
    try:
        r = conn.execute(
            "SELECT user_id, exp, level, username FROM users WHERE user_id = ?",
            [int(user_id)],
        ).fetchone()
    finally:
        conn.close()
    return _row(r) if r else None


def validate_update(level, exp):
    """Validiert exp/level (rein). Wirft LevelValidationError."""
    for name, value in (("level", level), ("exp", exp)):
        if isinstance(value, bool) or not isinstance(value, int):
            raise LevelValidationError(f"{name} muss eine Ganzzahl sein")
    if not (LEVEL_MIN <= level <= LEVEL_MAX):
        raise LevelValidationError(f"level muss zwischen {LEVEL_MIN} und {LEVEL_MAX} liegen")
    if not (EXP_MIN <= exp <= EXP_MAX):
        raise LevelValidationError(f"exp muss zwischen {EXP_MIN} und {EXP_MAX} liegen")
    return level, exp


def update_user(user_id, level, exp):
    """Gezieltes UPDATE; gibt betroffene Zeilenzahl zurück (0 = nicht gefunden)."""
    validate_update(level, exp)
    conn = _connect()
    try:
        cur = conn.execute(
            "UPDATE users SET level = ?, exp = ? WHERE user_id = ?",
            (level, exp, int(user_id)),
        )
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()
