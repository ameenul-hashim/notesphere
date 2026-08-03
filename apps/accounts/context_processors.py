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
