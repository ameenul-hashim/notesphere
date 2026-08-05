"""Field and password validators with the exact NoteSphere error messages.

These run on forms AND on the model, so every entry point (signup, forgot
password, admin tools, createsuperuser) enforces the same rules.
"""

import re

from django.core.exceptions import ValidationError

FULL_NAME_MIN_LENGTH = 3
FULL_NAME_MAX_LENGTH = 100
USERNAME_MIN_LENGTH = 4
USERNAME_MAX_LENGTH = 30
PHONE_LENGTH = 10
PASSWORD_MIN_LENGTH = 8


def validate_full_name(value):
    if not value or not value.strip():
        raise ValidationError("Full name is required.")
    if len(value) < FULL_NAME_MIN_LENGTH or len(value) > FULL_NAME_MAX_LENGTH:
        raise ValidationError("Full name must be between 3 and 100 characters.")
    if not re.fullmatch(r"[A-Za-z ]+", value):
        raise ValidationError("Full name must contain only letters and spaces.")


def validate_username(value):
    if not value or not value.strip():
        raise ValidationError("Username is required.")
    if len(value) < USERNAME_MIN_LENGTH or len(value) > USERNAME_MAX_LENGTH:
        raise ValidationError("Username must be between 4 and 30 characters.")
    if not re.fullmatch(r"[A-Za-z0-9_]+", value):
        raise ValidationError("Username must contain only letters, numbers and underscore.")


def validate_phone(value):
    if not value or not value.strip():
        return
    if not re.fullmatch(r"\d{10}", value):
        raise ValidationError("Phone number must contain exactly 10 digits.")


def validate_password_strength(value):
    if not value:
        raise ValidationError("Password is required.")
    if len(value) < PASSWORD_MIN_LENGTH:
        raise ValidationError("Password must contain at least 8 characters.")
    if not re.search(r"[A-Z]", value):
        raise ValidationError("Password must contain one uppercase letter.")
    if not re.search(r"[a-z]", value):
        raise ValidationError("Password must contain one lowercase letter.")
    if not re.search(r"\d", value):
        raise ValidationError("Password must contain one number.")
    if not re.search(r"[^A-Za-z0-9]", value):
        raise ValidationError("Password must contain one special character.")
