"""
Production settings.

Used when DJANGO_ENV == "production".
Production is not configured yet; when deploying, review and fill in the
secure defaults below and move the DATABASES block to Neon PostgreSQL
(see config/integrations/neon.py).
"""

from .base import *  # noqa: F401,F403

import os  # noqa: E402

DEBUG = False

# DJANGO_SECRET_KEY must be provided explicitly in production.
if not os.environ.get("DJANGO_SECRET_KEY"):
    raise RuntimeError(
        "DJANGO_SECRET_KEY is required in production. Set it in the environment or .env."
    )

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",")
    if host.strip()
]

# Collected static files live here (run: manage.py collectstatic).
STATIC_ROOT = BASE_DIR / "staticfiles"

# Security hardening (tune when you have TLS/HTTPS fully configured).
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_REFERRER_POLICY = "same-origin"

# TODO: switch to Neon PostgreSQL via config/integrations/neon.py when ready.
# from config.integrations.neon import get_database_config
# DATABASES = {"default": get_database_config()}
