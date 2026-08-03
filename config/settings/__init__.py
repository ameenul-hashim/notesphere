"""
Settings package for NoteSphere.

Loads environment variables from the project root `.env` file and selects the
active settings module based on the DJANGO_ENV variable:
    - "development" (default) -> config.settings.development
    - "production"            -> config.settings.production
"""

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

load_dotenv(PROJECT_ROOT / ".env", override=True)

DJANGO_ENV = os.environ.get("DJANGO_ENV", "development").lower()

if DJANGO_ENV == "production":
    from .production import *  # noqa: F401,F403
else:
    from .development import *  # noqa: F401,F403
