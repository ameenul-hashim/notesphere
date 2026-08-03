"""
Development settings.

Used when DJANGO_ENV is unset or equals "development" (the default).
"""

from .base import *  # noqa: F401,F403

DEBUG = True
