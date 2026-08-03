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
      (ACTIVE / INACTIVE / BLOCKED / DELETED).
    - `is_active` is auto-synced so that only DELETED accounts are rejected by
      Django's authentication backend; BLOCKED and INACTIVE accounts pass
      `authenticate()` and are then rejected by the login form with a
      specific message.
    """

    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        STUDENT = "STUDENT", "Student"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"
        BLOCKED = "BLOCKED", "Blocked"
        DELETED = "DELETED", "Deleted"

    full_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=10, unique=True)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.STUDENT)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)

    is_email_verified = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)

    password_changed_at = models.DateTimeField(null=True, blank=True)

    profile_image = models.ImageField(upload_to="profiles/", null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="deleted_students",
    )

    objects = UserManager()
    # Base manager used for related lookups and migrations: sees EVERYTHING,
    # including soft-deleted rows, so deleted students stay recoverable.
    all_objects = models.Manager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email", "phone", "full_name"]

    class Meta:
        ordering = ["-created_at"]
        base_manager_name = "all_objects"
        indexes = [
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        # Display rule: the username is a login credential and is never shown.
        return self.full_name

    def save(self, *args, **kwargs):
        if self.status == self.Status.DELETED:
            self.is_active = False
        else:
            self.is_active = True
        super().save(*args, **kwargs)


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
    """Scalable audit log of authentication and account actions."""

    class Action(models.TextChoices):
        LOGIN = "LOGIN", "Login"
        LOGOUT = "LOGOUT", "Logout"
        PASSWORD_CHANGED = "PASSWORD_CHANGED", "Password Changed"
        PASSWORD_RESET = "PASSWORD_RESET", "Password Reset"
        OTP_SENT = "OTP_SENT", "OTP Sent"
        OTP_VERIFIED = "OTP_VERIFIED", "OTP Verified"
        ACCOUNT_BLOCKED = "ACCOUNT_BLOCKED", "Account Blocked"
        ACCOUNT_UNBLOCKED = "ACCOUNT_UNBLOCKED", "Account Unblocked"
        ACCOUNT_DELETED = "ACCOUNT_DELETED", "Account Deleted"
        PROFILE_UPDATED = "PROFILE_UPDATED", "Profile Updated"

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
