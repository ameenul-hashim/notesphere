"""
URL configuration for the NoteSphere project.

Currently only the Django admin is mounted. Feature URLs will be added per app
(e.g. accounts, academics) as the project grows.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    # Root redirects to the login page.
    path("", RedirectView.as_view(pattern_name="accounts:login", permanent=False)),
    # Reserved for future Django admin use.
    path("admin/", admin.site.urls),
    # Custom admin interface.
    path("dashboard/", include("admins.urls")),
    path("dashboard/admin/login/", RedirectView.as_view(pattern_name="admins:admin_login", permanent=False)),
    # Student-facing authentication (supports both /login/ and /accounts/login/).
    path("", include("accounts.urls")),
    path("accounts/", include("accounts.urls")),
    # Academic features (semesters, later subjects).
    path("", include("academics.urls")),
    # Community Chat & Active Members.
    path("community/", include("community.urls")),
]

# Serve static/media files during development only.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
