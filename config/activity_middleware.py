"""Middleware that stamps each authenticated session with a last_active timestamp.

The presence system (community.views.online_users) uses this to distinguish
truly active sessions from stale ones that linger in the database after the
user closes the browser or loses connectivity.
"""


class ActivityStampMiddleware:
    """Write a UTC epoch into the session on every authenticated request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if hasattr(request, "user") and request.user.is_authenticated:
            import time

            request.session["last_active"] = int(time.time())
        return self.get_response(request)
