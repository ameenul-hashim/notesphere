"""
Neon PostgreSQL integration - PLACEHOLDER. NOT CONNECTED YET.

Planned activation steps (do this when you are ready to move off SQLite):
    1. Create a Neon project and copy its connection string.
    2. Add the following to `.env`:
           DB_ENGINE=postgresql
           PGDATABASE=<neon-db-name>
           PGUSER=<neon-user>
           PGPASSWORD=<neon-password>
           PGHOST=<neon-host>
           PGPORT=5432
    3. In `config/settings/base.py`, swap the SQLite DATABASES block for:
           from config.integrations.neon import get_database_config
           DATABASES = {"default": get_database_config()}
    4. Run `manage.py migrate` against the Neon database.

Nothing in this module runs until step 3 is done.
"""

import os


def get_database_config() -> dict:
    """Return a Django DATABASES 'default' entry pointing at Neon PostgreSQL."""
    if os.environ.get("DB_ENGINE", "").lower() != "postgresql":
        raise RuntimeError(
            "Neon PostgreSQL is not enabled. Set DB_ENGINE=postgresql in .env to enable."
        )

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
