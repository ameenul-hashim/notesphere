"""NoteSphere account models."""

import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

from .managers import UserManager


class User(AbstractUser):
    """A single user model for both students and admins.

    - `role` distinguishes ADMIN from STUDENT.
    - `status` is the single source of truth for account state
      (ACTIVE / INACTIVE / BLOCKED). Deletion is permanent: a deleted
      record is removed from the database entirely.
    - `theme` stores the user's preferred UI theme, applied via the
      `data-theme` attribute on `<html>`.
    """

    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        STUDENT = "STUDENT", "Student"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"
        BLOCKED = "BLOCKED", "Blocked"

    class Theme(models.TextChoices):
        CLASSIC_WHITE = "classic_white", "Classic White"
        MIDNIGHT_BLACK = "midnight_black", "Midnight Black"
        OCEAN_BLUE = "ocean_blue", "Ocean Blue"
        EMERALD_GREEN = "emerald_green", "Emerald Green"
        ROYAL_PURPLE = "royal_purple", "Royal Purple"
        SUNSET_ORANGE = "sunset_orange", "Sunset Orange"
        ROSE_PINK = "rose_pink", "Rose Pink"
        SLATE_GRAY = "slate_gray", "Slate Gray"
        CYBER_NEON = "cyber_neon", "Cyber Neon"
        COFFEE_BROWN = "coffee_brown", "Coffee Brown"

    full_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=10, unique=True)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.STUDENT)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    theme = models.CharField(
        max_length=30,
        choices=Theme.choices,
        default=Theme.CLASSIC_WHITE,
    )

    is_email_verified = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)

    password_changed_at = models.DateTimeField(null=True, blank=True)

    profile_image = models.ImageField(upload_to="profiles/", null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email", "phone", "full_name"]

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["role", "last_login"]),
        ]

    def __str__(self):
        # Display rule: the username is a login credential and is never shown.
        return self.full_name


class PasswordResetOTP(models.Model):
    """One-time, hashed, expiring OTP for password resets.

    `flow_id` is an unguessable UUID used as a capability token in the email
    link so the user lands directly on the OTP verification step.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="otps")
    flow_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    otp_hash = models.CharField(max_length=128)
    expires_at = models.DateTimeField()
    attempts = models.PositiveIntegerField(default=0)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"OTP for {self.user.full_name} (used={self.is_used})"

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at


class UserActivity(models.Model):
    """Audit log reserved for important account events only.

    Login timestamps live on `User.last_login`; this table intentionally does
    NOT record every login/logout. Only password resets, profile updates and
    block / unblock / delete actions are stored.
    """

    class Action(models.TextChoices):
        PASSWORD_RESET = "PASSWORD_RESET", "Password Reset"
        PROFILE_UPDATED = "PROFILE_UPDATED", "Profile Updated"
        ACCOUNT_BLOCKED = "ACCOUNT_BLOCKED", "Account Blocked"
        ACCOUNT_UNBLOCKED = "ACCOUNT_UNBLOCKED", "Account Unblocked"
        ACCOUNT_DELETED = "ACCOUNT_DELETED", "Account Deleted"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="activities")
    action = models.CharField(max_length=30, choices=Action.choices)
    detail = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    browser = models.CharField(max_length=100, blank=True)
    os = models.CharField(max_length=100, blank=True)
    device = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "created_at"]),
        ]

    def __str__(self):
        return f"{self.user.full_name} - {self.action}"
