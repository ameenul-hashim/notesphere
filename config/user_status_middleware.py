"""Middleware that logs out users whose account is no longer usable.

When an admin blocks (or deactivates) an account, any already-open session is
invalidated here: the user is logged out, their session and session cookie are
flushed, and they are redirected to the login page with a `blocked` flag.
"""

from django.conf import settings
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import reverse

INVALID_STATUSES = ("BLOCKED", "INACTIVE", "DELETED")


class UserStatusMiddleware:
    """Immediately log out authenticated users with a blocked/inactive status."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not (hasattr(request, "user") and request.user.is_authenticated):
            return self.get_response(request)

        if request.user.status in INVALID_STATUSES:
            logout(request)
            login_url = reverse(settings.LOGIN_URL)
            return redirect(f"{login_url}?blocked=1")

        return self.get_response(request)
