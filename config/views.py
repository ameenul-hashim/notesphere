"""Project-level utility views."""

from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET


@require_GET
@never_cache
@ensure_csrf_cookie
def csrf_refresh(request):
    """Return the current CSRF token and guarantee the cookie is set.

    ``csrf_refresh.js`` calls this when a page is restored from the
    back/forward cache or brought back into focus, so forms never submit a
    token that was rotated in another tab or during a previous login.
    """
    return JsonResponse({"csrfToken": get_token(request)})
