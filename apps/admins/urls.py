"""URL configuration for the custom admin interface (mounted under /dashboard/)."""

from django.urls import path

from . import views

app_name = "admins"

urlpatterns = [
    path("login/", views.admin_login, name="admin_login"),
    path("logout/", views.admin_logout, name="admin_logout"),
    path("", views.dashboard, name="dashboard"),
    path("profile/", views.profile, name="profile"),
    path("students/", views.student_list, name="student_list"),
    path("students/<int:pk>/", views.student_detail, name="student_detail"),
    path("students/<int:pk>/block/", views.block_student, name="block_student"),
    path("students/<int:pk>/unblock/", views.unblock_student, name="unblock_student"),
    path("students/<int:pk>/delete/", views.delete_student, name="delete_student"),
    path(
        "students/<int:pk>/reset-password/",
        views.initiate_student_password_reset,
        name="initiate_student_password_reset",
    ),
]
