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
        "USER_REGISTRY": user_registry,
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


DIWALI_GREETING_TITLE = "Happy Diwali!"
DIWALI_GREETING_MESSAGE = (
    "May this festival of lights bring happiness, knowledge, success and prosperity."
)


def festival(request):
    """Expose the date-gated festival state used by the shared layout.

    ``settings.DIWALI_ENABLED`` is the master switch. When on,
    ``DIWALI_START_DATE`` / ``DIWALI_END_DATE`` (ISO dates) form an inclusive
    range evaluated against the server's local date (``TIME_ZONE``), so the
    theme turns itself off automatically the day after the end date.

    The one-time greeting is remembered in the session so it is shown at most
    once per visit and never reappears when navigating between pages. To add a
    future festival, reuse the same ``festival_active`` / ``festival_name``
    contract and scope a new stylesheet to ``body[data-festival="<name>"]``.
    """
    from datetime import date

    from django.conf import settings
    from django.utils import timezone

    enabled = bool(getattr(settings, "DIWALI_ENABLED", True))
    try:
        start = date.fromisoformat(str(getattr(settings, "DIWALI_START_DATE", "")))
        end = date.fromisoformat(str(getattr(settings, "DIWALI_END_DATE", "")))
    except (TypeError, ValueError):
        return {
            "diwali_active": False,
            "festival_active": False,
            "festival_name": "",
            "diwali_greeting": False,
        }

    active = enabled and start <= timezone.localdate() <= end
    show_greeting = False
    if active:
        try:
            seen = bool(request.session.get("ns_diwali_greeted", False))
        except Exception:
            seen = True
        if not seen:
            show_greeting = True
            try:
                request.session["ns_diwali_greeted"] = True
            except Exception:
                pass

    return {
        "diwali_active": active,
        "festival_active": active,
        "festival_name": "diwali" if active else "",
        "diwali_greeting": show_greeting,
        "diwali_greeting_title": DIWALI_GREETING_TITLE,
        "diwali_greeting_message": DIWALI_GREETING_MESSAGE,
    }





