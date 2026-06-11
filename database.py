"""Zentrale SQLite-Verbindung für das Levelsystem.

Der DB-Pfad ist via Umgebungsvariable ``DB_PATH`` konfigurierbar
(Default: ./level_system.db) — vorbereitet für Docker-Volumes.
"""
import os
import sqlite3

DB_PATH = os.environ.get("DB_PATH", "./level_system.db")

_connection = None


def get_connection():
    """Liefert die (lazy initialisierte) SQLite-Verbindung inkl. Schema."""
    global _connection
    if _connection is None:
        _connection = sqlite3.connect(DB_PATH)
        _connection.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                exp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1
            )
        ''')
        _connection.commit()
    return _connection


def calculate_exp(level):
    """Benötigte EXP für ein Level-Up auf dem gegebenen Level."""
    if level <= 15:
        return 100
    elif level <= 25:
        return 125
    elif level <= 50:
        return 250
    elif level <= 75:
        return 375
    elif level <= 100:
        return 500
    elif level <= 125:
        return 625
    elif level <= 150:
        return 750
    elif level <= 175:
        return 875
    else:
        return 1000
