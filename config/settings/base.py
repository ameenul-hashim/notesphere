"""
Base settings shared by every environment.

Environment variables (see `.env.example`) are read here. Common configuration
lives in this module; environment-specific overrides live in
`development.py` and `production.py`.
"""

import os
import sys
from pathlib import Path

from django.core.management.utils import get_random_secret_key

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Make the `apps/` package importable, e.g. `accounts` instead of `apps.accounts`.
sys.path.append(str(BASE_DIR / "apps"))

# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------

# Fallback to a generated key so the project runs out of the box in
# development. Production MUST set DJANGO_SECRET_KEY in the environment.
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", get_random_secret_key())

DEBUG = os.environ.get("DJANGO_DEBUG", "True").lower() == "true"

raw_allowed_hosts = os.environ.get("DJANGO_ALLOWED_HOSTS", "*")
ALLOWED_HOSTS = [
    host.strip().strip('"').strip("'")
    for host in raw_allowed_hosts.split(",")
    if host.strip()
]
if not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ["*"]

raw_csrf_origins = os.environ.get("CSRF_TRUSTED_ORIGINS", "https://*.up.railway.app,https://*.railway.app")
CSRF_TRUSTED_ORIGINS = [
    origin.strip().strip('"').strip("'")
    for origin in raw_csrf_origins.split(",")
    if origin.strip()
]


# ---------------------------------------------------------------------------
# Application definition
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # NoteSphere apps
    "accounts",
    "students",
    "admins",
    "academics",
    "community",
]

MIDDLEWARE = [
    "config.diagnostics_middleware.ProductionDiagnosticsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

CSRF_FAILURE_VIEW = "config.diagnostics_middleware.custom_csrf_failure_logger"



ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "accounts.context_processors.active_theme",
                "accounts.context_processors.firebase_config",
                "accounts.context_processors.user_notifications",
            ],
        },
    },
]

# ---------------------------------------------------------------------------
# Firebase (Cloud Firestore) — Frontend Web SDK configuration
# Passed to frontend via context processor / window.FIREBASE_CONFIG
# ---------------------------------------------------------------------------
FIREBASE_CONFIG = {
    "apiKey": os.environ.get("FIREBASE_API_KEY", ""),
    "authDomain": os.environ.get("FIREBASE_AUTH_DOMAIN", "your-project-id.firebaseapp.com"),
    "projectId": os.environ.get("FIREBASE_PROJECT_ID", "your-project-id"),
    "storageBucket": os.environ.get("FIREBASE_STORAGE_BUCKET", "your-project-id.firebasestorage.app"),
    "messagingSenderId": os.environ.get("FIREBASE_MESSAGING_SENDER_ID", ""),
    "appId": os.environ.get("FIREBASE_APP_ID", ""),
}

# Path to the Firebase service account JSON (backend Admin SDK only, NEVER exposed to frontend)
# This file is gitignored. Set this env var in production for a custom location.
FIREBASE_SERVICE_ACCOUNT_PATH = os.environ.get(
    "FIREBASE_SERVICE_ACCOUNT_PATH",
    str(BASE_DIR / "config" / "firebase" / "firebase-service-account.json"),
)



WSGI_APPLICATION = "config.wsgi.application"

# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

# Custom user model (accounts.User) - set before the one-time schema reset.
AUTH_USER_MODEL = "accounts.User"

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "accounts:student_dashboard"
LOGOUT_REDIRECT_URL = "accounts:login"

# ---------------------------------------------------------------------------
# Database
#
# Neon PostgreSQL - credentials are read from .env via
# config/integrations/neon.py. SQLite is no longer used.
# ---------------------------------------------------------------------------

from config.integrations.neon import get_database_config  # noqa: E402

DATABASES = {"default": get_database_config()}

# ---------------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Asia/Qatar"

USE_I18N = True

USE_TZ = True

# ---------------------------------------------------------------------------
# Static files & media
# ---------------------------------------------------------------------------

STATIC_URL = "static/"

STATICFILES_DIRS = [BASE_DIR / "static"]

STATIC_ROOT = BASE_DIR / "staticfiles"

STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}



MEDIA_URL = "media/"


MEDIA_ROOT = BASE_DIR / "media"

# ---------------------------------------------------------------------------
# Email — Brevo SMTP (transactional provider)
#
# All outbound email (OTP, password reset, support) goes through Brevo.
# Set BREVO_* vars in .env. The EMAIL_* aliases point to the same values so
# Django's built-in backends work without extra configuration.
# ---------------------------------------------------------------------------

EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend",
)

# Brevo SMTP relay
EMAIL_HOST     = os.environ.get("BREVO_SMTP_HOST",     "smtp-relay.brevo.com")
EMAIL_PORT     = int(os.environ.get("BREVO_SMTP_PORT", "587"))
EMAIL_HOST_USER     = os.environ.get("BREVO_SMTP_USER",     "")
EMAIL_HOST_PASSWORD = os.environ.get("BREVO_SMTP_PASSWORD", "")
EMAIL_USE_TLS  = os.environ.get("EMAIL_USE_TLS", "True").lower()  == "true"
EMAIL_USE_SSL  = os.environ.get("EMAIL_USE_SSL", "False").lower() == "true"

# Sender identity shown in every outbound email
BREVO_FROM_NAME  = os.environ.get("BREVO_FROM_NAME",  "NoteSphere")
BREVO_FROM_EMAIL = os.environ.get("BREVO_FROM_EMAIL", EMAIL_HOST_USER)

DEFAULT_FROM_EMAIL = f"{BREVO_FROM_NAME} <{BREVO_FROM_EMAIL}>"

# Support inbox — where student help emails are delivered
SUPPORT_EMAIL = os.environ.get("SUPPORT_EMAIL", "noreply@notesphere.com")

# ---------------------------------------------------------------------------
# Default primary key field type
# ---------------------------------------------------------------------------

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
