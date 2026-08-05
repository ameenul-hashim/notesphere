"""NoteSphere account models."""

import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.templatetags.static import static
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
        NAVY_DARK = "navy_dark", "Navy Dark"
        FOREST_TEAL = "forest_teal", "Forest Teal"
        CRIMSON_RED = "crimson_red", "Crimson Red"
        LAVENDER_LIGHT = "lavender_light", "Lavender"
        MINT_LIGHT = "mint_light", "Mint"

    full_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=10, unique=True, null=True, blank=True)
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

    avatar = models.ForeignKey(
        "Avatar",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="users",
    )

    photo = models.ImageField(
        upload_to="avatars/",
        max_length=500,
        null=True,
        blank=True,
        help_text="Custom profile photo (admins). Rendered in place of the avatar.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email", "full_name"]

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["role", "last_login"]),
        ]

    def __str__(self):
        # Display rule: the username is a login credential and is never shown.
        return self.full_name

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    def get_avatar_url(self):
        """Resolve the best available avatar image URL for this user.

        Priority: custom photo > uploaded avatar image > built-in library PNG
        (matching the `_avatar_picture.html` fallback). Never raises: any
        missing or unreadable image falls back to a default library PNG.
        """
        try:
            if self.photo and getattr(self.photo, "url", None):
                return self.photo.url
        except Exception:
            pass

        avatar = self.avatar
        if avatar is not None:
            try:
                if avatar.image and getattr(avatar.image, "url", None):
                    return avatar.image.url
            except Exception:
                pass

            if avatar.gender == "female" and 1 <= avatar.display_order <= 5:
                return static(f"images/avatars/avatar_female_{avatar.display_order}.png")
            if avatar.gender == "male" and 11 <= avatar.display_order <= 15:
                return static(f"images/avatars/avatar_male_{avatar.display_order - 10}.png")

        return static("images/avatars/avatar_male_1.png")


class Avatar(models.Model):
    """A selectable avatar from the built-in professional library.

    Ten built-in avatars exist (5 male + 5 female) in a modern flat-illustration
    style, served as static PNG images referenced by gender + display order.
    Admins can add, edit and delete avatars; a custom avatar without an image
    falls back to the static PNG matching its gender + display order.
    """

    class Gender(models.TextChoices):
        MALE = "male", "Male"
        FEMALE = "female", "Female"

    name = models.CharField(
        max_length=60,
        blank=True,
        help_text="Display name, e.g. \"Professional Woman 1\".",
    )
    image = models.ImageField(
        upload_to="avatars/library/",
        null=True,
        blank=True,
        help_text="Optional uploaded image. When set, it is used instead of the static illustration.",
    )
    icon_path = models.TextField(blank=True, help_text="Inline SVG portrait markup (viewBox 0 0 96 96).")
    color_from = models.CharField(max_length=7, default="#6366f1")
    color_to = models.CharField(max_length=7, default="#8b5cf6")
    gender = models.CharField(max_length=10, choices=Gender.choices, default=Gender.MALE)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "pk"]

    def __str__(self):
        return self.name or f"Avatar {self.pk} ({self.get_gender_display()})"

    @property
    def gradient(self):
        return f"linear-gradient(135deg, {self.color_from}, {self.color_to})"


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
