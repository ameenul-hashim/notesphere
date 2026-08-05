"""Middleware that logs out authenticated users after a period of inactivity.

It relies on the `last_active` epoch stamped by `ActivityStampMiddleware`.
When a user's session has been idle for more than `SESSION_IDLE_TIMEOUT_MINUTES`
they are automatically logged out, their session and session cookie are
flushed, and they are redirected to the login page with a `session_expired` flag.
"""

import time

from django.conf import settings
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import reverse


class IdleTimeoutMiddleware:
    """Log out authenticated users after SESSION_IDLE_TIMEOUT_MINUTES of inactivity."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not (hasattr(request, "user") and request.user.is_authenticated):
            return self.get_response(request)

        timeout_minutes = getattr(settings, "SESSION_IDLE_TIMEOUT_MINUTES", 30)
        timeout_seconds = timeout_minutes * 60

        last_active = request.session.get("last_active")
        if last_active is None:
            last_active = int(time.time())

        if int(time.time()) - last_active > timeout_seconds:
            logout(request)
            login_url = reverse(settings.LOGIN_URL)
            return redirect(f"{login_url}?session_expired=1")

        return self.get_response(request)
