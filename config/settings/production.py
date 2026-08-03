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

# Cloudflare / reverse proxy SSL headers
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

# Security hardening
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "True").lower() == "true"
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_REFERRER_POLICY = "same-origin"

# Database connection: Neon PostgreSQL
from config.integrations.neon import get_database_config  # noqa: E402
DATABASES = {"default": get_database_config()}

