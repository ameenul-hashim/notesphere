"""Template context processors shared across all pages."""

import logging

from .models import User

logger = logging.getLogger(__name__)

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
    custom_token = ""
    if request.user.is_authenticated:
        user_data = {
            "id": request.user.id,
            "username": request.user.username,
            "full_name": format_clean_name(request.user.full_name),
            "role": request.user.role,
            "is_admin": request.user.is_admin,
            "avatar_id": getattr(request.user, "avatar_id", None),
            "avatar_url": request.user.get_avatar_url(),
        }

        # Mint a fresh Firebase custom token for the authenticated Django user.
        # Django auth is the source of truth; the token maps the Django session
        # onto a Firebase Auth identity so Firestore security rules can verify
        # request.auth on the client. UID == str(user.id) so that Firestore
        # rules (e.g. users/user_$(request.auth.uid)) resolve correctly.
        try:
            from config.integrations.firebase_admin_sdk import create_custom_token

            custom_token = create_custom_token(str(request.user.id))
        except Exception as exc:
            logger.warning("Could not create Firebase custom token for user %s: %s", request.user.id, exc)
            custom_token = ""

    fb_config = getattr(settings, "FIREBASE_CONFIG", {})

    user_registry = {}
    if request.user.is_authenticated:
        # Build registry for user resolution in chat
        for user in User.objects.filter(is_active=True).select_related("avatar"):
            user_registry[user.id] = {
                "name": format_clean_name(user.full_name),
                "role": user.role,
                "avatar_url": user.get_avatar_url(),
            }

    return {
        "FIREBASE_CONFIG": fb_config,
        "FIREBASE_CONFIG_JSON": json.dumps(fb_config),
        "CURRENT_USER_JSON": user_data,
        "CURRENT_USER_JSON_STR": json.dumps(user_data),
        "FIREBASE_CUSTOM_TOKEN": custom_token,
        "FIREBASE_CUSTOM_TOKEN_JSON": json.dumps(custom_token),
        "USER_REGISTRY_JSON_STR": json.dumps(user_registry),
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





