"""
Custom user manager for NoteSphere.

The default manager (`objects`) hides DELETED accounts so the app only ever
sees live users. `all_objects` (the base manager) includes everything so
soft-deleted students always remain recoverable.
"""

from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):
    """Manager for the custom User model.

    Used as the default manager; excludes DELETED accounts from queries.
    """

    use_in_migrations = True

    def get_queryset(self):
        return super().get_queryset().exclude(status="DELETED")

    def create_user(self, username, email, phone, full_name, password=None, **extra_fields):
        if not username:
            raise ValueError("The username must be set.")
        if not email:
            raise ValueError("The email must be set.")
        if not phone:
            raise ValueError("The phone number must be set.")

        email = self.normalize_email(email)
        user = self.model(
            username=username,
            email=email,
            phone=phone,
            full_name=full_name,
            **extra_fields,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, phone, full_name, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", "ADMIN")
        extra_fields.setdefault("status", "ACTIVE")

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(username, email, phone, full_name, password, **extra_fields)
