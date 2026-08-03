"""Template context processors shared across all pages."""

from .models import User

DEFAULT_THEME = User.Theme.CLASSIC_WHITE


def active_theme(request):
    """Expose the active theme for the `data-theme` attribute on `<html>`.

    Authenticated users use their saved theme (from the DB). Anonymous users
    fall back to the default theme; the pre-paint script may override that
    from localStorage for guest browsing.
    """
    if request.user.is_authenticated:
        theme = getattr(request.user, "theme", None)
        if theme in User.Theme.values:
            return {"active_theme": theme}
    return {"active_theme": DEFAULT_THEME}


def firebase_config(request):
    """Expose Firebase configuration and logged-in user profile info to frontend JS."""
    import json
    from django.conf import settings
    from community.utils import format_clean_name

    user_data = None
    if request.user.is_authenticated:
        user_data = {
            "id": request.user.id,
            "username": request.user.username,
            "full_name": format_clean_name(request.user.full_name),
            "role": request.user.role,
            "is_admin": request.user.is_admin,
            "avatar_id": getattr(request.user, "avatar_id", None),
        }

    fb_config = getattr(settings, "FIREBASE_CONFIG", {})

    return {
        "FIREBASE_CONFIG": fb_config,
        "FIREBASE_CONFIG_JSON": json.dumps(fb_config),
        "CURRENT_USER_JSON": user_data,
        "CURRENT_USER_JSON_STR": json.dumps(user_data),
    }


def user_notifications(request):
    """Expose unread notifications to topbar bell icon, auto-deleting notifications older than 7 days."""
    if request.user.is_authenticated:
        from datetime import timedelta
        from django.utils import timezone
        from community.models import Notification

        # Auto-delete notifications older than 7 days
        cutoff = timezone.now() - timedelta(days=7)
        Notification.objects.filter(user=request.user, created_at__lt=cutoff).delete()

        unread = Notification.objects.filter(user=request.user, is_read=False)[:10]
        return {
            "topbar_notifications": unread,
            "unread_notifications_count": Notification.objects.filter(user=request.user, is_read=False).count(),
        }
    return {
        "topbar_notifications": [],
        "unread_notifications_count": 0,
    }





