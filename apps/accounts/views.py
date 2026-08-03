"""Student-facing authentication views."""

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import redirect, render

from .decorators import student_required
from .forms import (
    ForgotPasswordForm,
    LoginForm,
    OTPVerifyForm,
    SetNewPasswordForm,
    SignUpForm,
)
from academics.models import Semester
from .models import PasswordResetOTP, User, UserActivity
from .services import create_and_send_otp, set_password_and_track


def redirect_after_login(user):
    if user.role == User.Role.ADMIN:
        return redirect("admins:dashboard")
    return redirect("accounts:student_dashboard")


def signup(request):
    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Account created successfully. Please log in.")
        return redirect("accounts:login")
    return render(request, "accounts/signup.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect_after_login(request.user)

    form = LoginForm(request.POST or None, request=request, allowed_role=User.Role.STUDENT)
    if request.method == "POST" and form.is_valid():
        user = form.cleaned_data["user"]
        login(request, user)
        return redirect_after_login(user)
    return render(request, "accounts/login.html", {"form": form})


@login_required
def logout_view(request):
    if request.method == "POST":
        logout(request)
        messages.success(request, "You have been logged out.")
    return redirect("accounts:login")


def forgot_password(request):
    form = ForgotPasswordForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.cleaned_data["user"]
        otp_obj = create_and_send_otp(user, request)
        request.session["reset_flow_id"] = str(otp_obj.flow_id)
        messages.info(request, "An OTP has been sent to your email.")
        return redirect("accounts:otp_verify")
    return render(request, "accounts/forgot_password.html", {"form": form})


def get_otp_by_flow(flow_id):
    if not flow_id:
        return None
    try:
        return PasswordResetOTP.objects.get(flow_id=flow_id, is_used=False)
    except PasswordResetOTP.DoesNotExist:
        return None


def otp_verify(request):
    flow_id = request.GET.get("flow") or request.session.get("reset_flow_id")
    otp_obj = get_otp_by_flow(flow_id)

    if otp_obj is None:
        messages.error(request, "Invalid or expired password reset link.")
        return redirect("accounts:forgot_password")

    form = OTPVerifyForm(request.POST or None, otp_obj=otp_obj)
    if request.method == "POST" and form.is_valid():
        request.session["reset_flow_id"] = str(otp_obj.flow_id)
        return redirect("accounts:reset_password")

    return render(request, "accounts/otp_verify.html", {"form": form})


def reset_password(request):
    flow_id = request.session.get("reset_flow_id") or request.GET.get("flow")
    otp_obj = get_otp_by_flow(flow_id)

    if otp_obj is None:
        messages.error(request, "Invalid or expired password reset session.")
        return redirect("accounts:forgot_password")

    if otp_obj.is_expired:
        messages.error(request, "This OTP has expired. Please request a new one.")
        return redirect("accounts:forgot_password")

    form = SetNewPasswordForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = otp_obj.user
        set_password_and_track(
            user,
            form.cleaned_data["password"],
            request,
            action=UserActivity.Action.PASSWORD_RESET,
            detail="Password reset via OTP flow",
        )
        otp_obj.is_used = True
        otp_obj.save(update_fields=["is_used"])
        messages.success(request, "Password reset successfully. Please log in.")
        return redirect("accounts:login")

    return render(request, "accounts/reset_password.html", {"form": form})


@login_required
def save_theme(request):
    """Persist the logged-in user's selected theme (used by the theme picker)."""
    if request.method == "POST":
        theme = request.POST.get("theme", "")
        if theme in User.Theme.values:
            request.user.theme = theme
            request.user.save(update_fields=["theme", "updated_at"])
            return JsonResponse({"ok": True})
    return JsonResponse({"ok": False}, status=400)


@login_required
@student_required
def student_dashboard(request):
    active_semesters = (
        Semester.objects.filter(status=Semester.Status.ACTIVE)
        .annotate(subject_count=Count("subjects", filter=Q(subjects__status="ACTIVE")))
    )
    return render(request, "accounts/student_dashboard.html", {"active_semesters": active_semesters})
