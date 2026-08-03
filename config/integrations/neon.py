"""
Neon PostgreSQL integration with SQLite fallback for development and unit testing.

Environment variables read from .env:
    DB_ENGINE=postgresql
    PGDATABASE=<neon-db-name>
    PGUSER=<neon-user>
    PGPASSWORD=<neon-password>
    PGHOST=<neon-host>
    PGPORT=5432
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

from urllib.parse import urlparse

def get_database_config() -> dict:
    """Return Django DATABASES 'default' entry for PostgreSQL (Neon/Railway) or SQLite fallback."""
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        parsed = urlparse(db_url)
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": parsed.path.lstrip("/"),
            "USER": parsed.username or "",
            "PASSWORD": parsed.password or "",
            "HOST": parsed.hostname or "",
            "PORT": str(parsed.port or 5432),
            "CONN_MAX_AGE": 60,
            "OPTIONS": {"sslmode": "require"},
        }

    if os.environ.get("DB_ENGINE", "").lower() == "postgresql":
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("PGDATABASE", "notesphere"),
            "USER": os.environ.get("PGUSER", ""),
            "PASSWORD": os.environ.get("PGPASSWORD", ""),
            "HOST": os.environ.get("PGHOST", ""),
            "PORT": os.environ.get("PGPORT", "5432"),
            "CONN_MAX_AGE": 60,
            "OPTIONS": {"sslmode": "require"},
        }


    return {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
