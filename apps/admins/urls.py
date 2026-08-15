"""URL configuration for the custom admin interface (mounted under /dashboard/)."""

from django.urls import path

from . import views

app_name = "admins"

urlpatterns = [
    path("admin/login/", views.admin_login, name="admin_login"),
    path("login/", views.admin_login),
    path("logout/", views.admin_logout, name="admin_logout"),
    path("", views.dashboard, name="dashboard"),
    path("profile/", views.profile, name="profile"),
    path("settings/", views.appearance, name="appearance"),
    path("avatars/", views.avatar_list, name="avatar_list"),
    path("avatars/add/", views.avatar_add, name="avatar_add"),
    path("avatars/<int:pk>/edit/", views.avatar_edit, name="avatar_edit"),
    path("avatars/<int:pk>/delete/", views.avatar_delete, name="avatar_delete"),
    path("students/", views.student_list, name="student_list"),
    path("students/<int:pk>/", views.student_detail, name="student_detail"),
    path("students/<int:pk>/block/", views.block_student, name="block_student"),
    path("students/<int:pk>/unblock/", views.unblock_student, name="unblock_student"),
    path("students/<int:pk>/delete/", views.delete_student, name="delete_student"),
]
