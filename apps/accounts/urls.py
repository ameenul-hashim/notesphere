"""URL configuration for the accounts app."""

from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("signup/", views.signup, name="signup"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("forgot-password/", views.forgot_password, name="forgot_password"),
    path("forgot-password/otp/", views.otp_verify, name="otp_verify"),
    path("forgot-password/reset/", views.reset_password, name="reset_password"),
    path("dashboard/student/", views.student_dashboard, name="student_dashboard"),
    path("dashboard/student/profile/", views.student_profile, name="student_profile"),
    path("dashboard/student/avatar/", views.student_avatar, name="student_avatar"),
    path("dashboard/student/support/", views.student_support, name="student_support"),
    path("theme/", views.save_theme, name="save_theme"),
]
