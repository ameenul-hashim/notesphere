"""
Production settings.

Used when DJANGO_ENV == "production".
Production is not configured yet; when deploying, review and fill in the
secure defaults below and move the DATABASES block to Neon PostgreSQL
(see config/integrations/neon.py).
"""

from .base import *  # noqa: F401,F403

import os  # noqa: E402
import logging  # noqa: E402

DEBUG = False

# DJANGO_SECRET_KEY must be provided explicitly in production.
if not os.environ.get("DJANGO_SECRET_KEY"):
    raise RuntimeError(
        "DJANGO_SECRET_KEY is required in production. Set it in the environment or .env."
    )

raw_allowed_hosts = os.environ.get("DJANGO_ALLOWED_HOSTS", "*")
ALLOWED_HOSTS = [
    host.strip().strip('"').strip("'")
    for host in raw_allowed_hosts.split(",")
    if host.strip()
]
if not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ["*"]


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


# ---------------------------------------------------------------------------
# STARTUP DIAGNOSTICS — log email env vars once when Django loads
# ---------------------------------------------------------------------------

def _log_startup_email_diagnostics():
    """Print email-related env var status once at startup (secrets masked)."""
    _log = logging.getLogger("django.server")
    api_key = os.environ.get("BREVO_API_KEY", "")
    smtp_user = os.environ.get("BREVO_SMTP_USER", "")
    smtp_pass = os.environ.get("BREVO_SMTP_PASSWORD", "")

    def _mask(k):
        if not k or len(k) < 16:
            return "***NOT_SET***"
        return f"{k[:8]}...{k[-4:]}"

    _log.info("=" * 60)
    _log.info("STARTUP EMAIL DIAGNOSTICS (production)")
    _log.info("=" * 60)
    _log.info("BREVO_API_KEY       = %s (masked: %s)", "SET" if api_key else "NOT SET", _mask(api_key))
    _log.info("BREVO_SMTP_USER     = %s", smtp_user or "(empty)")
    _log.info("BREVO_SMTP_PASSWORD = %s", "SET" if smtp_pass else "NOT SET")
    _log.info("BREVO_FROM_EMAIL    = %s", os.environ.get("BREVO_FROM_EMAIL", "(empty)"))
    _log.info("BREVO_FROM_NAME     = %s", os.environ.get("BREVO_FROM_NAME", "(empty)"))
    _log.info("SUPPORT_EMAIL       = %s", os.environ.get("SUPPORT_EMAIL", "(empty)"))
    _log.info("EMAIL_BACKEND       = %s", os.environ.get("EMAIL_BACKEND", "(not set, defaults to smtp)"))
    _log.info("EMAIL_HOST          = %s", os.environ.get("BREVO_SMTP_HOST", "(not set)"))
    _log.info("EMAIL_PORT          = %s", os.environ.get("BREVO_SMTP_PORT", "(not set)"))
    _log.info("=" * 60)

try:
    _log_startup_email_diagnostics()
except Exception:
    pass

