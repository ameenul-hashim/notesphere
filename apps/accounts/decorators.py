"""Reusable view decorators."""

from django.contrib.auth.decorators import login_required, user_passes_test

from .models import User


def role_required(*roles):
    """Restrict a view to authenticated users whose role is in `roles`."""
    def check(user):
        return user.is_authenticated and user.role in roles

    return user_passes_test(check, login_url="accounts:login")


student_required = role_required(User.Role.STUDENT)
admin_required = role_required(User.Role.ADMIN)
