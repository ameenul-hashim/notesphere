"""Student-facing authentication views."""

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMessage  # noqa: F401 – kept for future use
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import redirect, render

from .decorators import student_required
from .forms import (
    AvatarSelectionForm,
    ChangePasswordForm,
    ForgotPasswordForm,
    LoginForm,
    OTPVerifyForm,
    SetNewPasswordForm,
    SignUpForm,
    StudentContactForm,
    StudentUsernameForm,
)
from academics.models import Semester
from .models import Avatar, PasswordResetOTP, User
from .services import create_and_send_otp, send_transactional_email, set_password_and_track


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
        request.session.flush()
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
        set_password_and_track(user, form.cleaned_data["password"])
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
    semesters = (
        Semester.objects.order_by("display_order", "-created_at")
        .annotate(subject_count=Count("subjects", filter=Q(subjects__status="ACTIVE")))
    )
    return render(request, "accounts/student_dashboard.html", {"semesters": semesters})


@login_required
@student_required
def student_profile(request):
    """Student-only profile page: contact details, username, avatar and password.

    The profile picture (avatar picker) sits in a separate aside column and
    always shows the current image + username at the top.
    """
    contact_form = StudentContactForm(instance=request.user)
    username_form = StudentUsernameForm(instance=request.user)
    avatar_form = AvatarSelectionForm(instance=request.user)
    password_form = ChangePasswordForm(user=request.user)

    if request.method == "POST":
        if "save_contact" in request.POST:
            contact_form = StudentContactForm(instance=request.user, data=request.POST)
            if contact_form.is_valid():
                contact_form.save()
                messages.success(request, "Contact details updated successfully.")
                return redirect("accounts:student_profile")
        elif "save_username" in request.POST:
            username_form = StudentUsernameForm(instance=request.user, data=request.POST)
            if username_form.is_valid():
                username_form.save()
                messages.success(request, "Username updated successfully.")
                return redirect("accounts:student_profile")
        elif "save_avatar" in request.POST:
            avatar_form = AvatarSelectionForm(instance=request.user, data=request.POST)
            if avatar_form.is_valid():
                avatar_form.save()
                messages.success(request, "Avatar updated successfully.")
                return redirect("accounts:student_profile")
        elif "change_password" in request.POST:
            password_form = ChangePasswordForm(user=request.user, data=request.POST)
            if password_form.is_valid():
                set_password_and_track(
                    request.user,
                    password_form.cleaned_data["new_password"],
                )
                messages.success(request, "Password changed successfully.")
                return redirect("accounts:student_profile")

    return render(
        request,
        "accounts/student_profile.html",
        {
            "profile_user": request.user,
            "contact_form": contact_form,
            "username_form": username_form,
            "avatar_form": avatar_form,
            "avatar_value": avatar_form["avatar"].value(),
            "avatars": Avatar.objects.filter(is_active=True),
            "password_form": password_form,
        },
    )


@login_required
@student_required
def student_avatar(request):
    """Dedicated page for selecting and updating student profile avatar."""
    if not request.user.avatar:
        default_avatar = Avatar.objects.filter(is_active=True).first()
        if default_avatar:
            request.user.avatar = default_avatar
            request.user.save(update_fields=["avatar", "updated_at"])

    avatar_form = AvatarSelectionForm(instance=request.user)
    if request.method == "POST":
        avatar_form = AvatarSelectionForm(instance=request.user, data=request.POST)
        if avatar_form.is_valid():
            avatar_form.save()
            messages.success(request, "Profile avatar updated successfully.")
            return redirect("accounts:student_avatar")

    return render(
        request,
        "accounts/student_avatar.html",
        {
            "profile_user": request.user,
            "avatar_form": avatar_form,
            "avatar_value": avatar_form["avatar"].value(),
            "avatars": Avatar.objects.filter(is_active=True),
        },
    )


@login_required
@student_required
@login_required
def student_support(request):
    """Student support page — emails sent via Brevo through send_transactional_email()."""
    if request.method == "POST":
        import logging
        _view_logger = logging.getLogger("accounts.views")
        subject      = request.POST.get("subject", "").strip()
        message_text = request.POST.get("message", "").strip()

        _view_logger.info("=" * 60)
        _view_logger.info("STUDENT_SUPPORT VIEW - POST RECEIVED")
        _view_logger.info("User            = %s (pk=%s)", request.user.username, request.user.pk)
        _view_logger.info("User Email      = %s", request.user.email)
        _view_logger.info("Subject         = %s", subject)
        _view_logger.info("Message Length  = %d chars", len(message_text))
        _view_logger.info("=" * 60)

        if not subject or not message_text:
            messages.error(request, "Please fill out both subject and description.")
        else:
            support_email = getattr(settings, "SUPPORT_EMAIL", getattr(settings, "EMAIL_HOST_USER", ""))
            phone_display = request.user.phone or "-"

            text_body = (
                f"Support Request from Student\n"
                f"{'=' * 40}\n"
                f"Name     : {request.user.full_name}\n"
                f"Username : {request.user.username}\n"
                f"Email    : {request.user.email}\n"
                f"Phone    : {phone_display}\n"
                f"{'=' * 40}\n\n"
                f"Subject  : {subject}\n\n"
                f"Message:\n{message_text}"
            )
            html_body = f"""
<div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;padding:24px;background:#fff;border:1px solid #e5e7eb;border-radius:8px;">
  <h2 style="color:#111827;margin-top:0;">Support Request</h2>
  <table style="width:100%;font-size:14px;color:#374151;margin-bottom:16px;">
    <tr><td style="padding:4px 0;"><strong>Name</strong></td><td>{request.user.full_name}</td></tr>
    <tr><td style="padding:4px 0;"><strong>Username</strong></td><td>@{request.user.username}</td></tr>
    <tr><td style="padding:4px 0;"><strong>Email</strong></td><td>{request.user.email}</td></tr>
    <tr><td style="padding:4px 0;"><strong>Phone</strong></td><td>{phone_display}</td></tr>
    <tr><td style="padding:4px 0;"><strong>Subject</strong></td><td>{subject}</td></tr>
  </table>
  <div style="background:#f3f4f6;border-radius:6px;padding:16px;">
    <p style="margin:0;color:#374151;white-space:pre-wrap;">{message_text}</p>
  </div>
  <p style="color:#9ca3af;font-size:12px;margin-top:16px;">Reply directly to this email to respond to the student.</p>
</div>
"""

            _view_logger.info("Calling send_transactional_email()...")
            _view_logger.info("  to        = %s", support_email)
            _view_logger.info("  subject   = [NoteSphere Support] %s -- from %s", subject, request.user.full_name)
            _view_logger.info("  reply_to  = %s", request.user.email)

            ok = send_transactional_email(
                to        = support_email,
                subject   = f"[NoteSphere Support] {subject} — from {request.user.full_name}",
                text_body = text_body,
                html_body = html_body,
                reply_to  = [request.user.email] if request.user.email else None,
            )

            _view_logger.info("send_transactional_email() returned: %s", ok)

            if ok:
                messages.success(request, "Your support message has been sent successfully!")
            else:
                messages.error(
                    request,
                    f"Failed to send email. Please try again or contact support at {support_email}.",
                )
            return redirect("accounts:student_support")

    return render(request, "accounts/support.html", {"profile_user": request.user})

