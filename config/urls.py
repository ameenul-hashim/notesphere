"""
URL configuration for the NoteSphere project.

Currently only the Django admin is mounted. Feature URLs will be added per app
(e.g. accounts, academics) as the project grows.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    # Reserved for future Django admin use.
    path("admin/", admin.site.urls),
    # Custom admin interface.
    path("dashboard/", include("admins.urls")),
    # Student-facing authentication.
    path("", include("accounts.urls")),
]

# Serve static/media files during development only.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
