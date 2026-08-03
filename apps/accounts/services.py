"""Business services for the authentication module.

Keeps views thin and centralizes OTP, email, and activity-logging behaviour.
"""

import secrets

from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from .models import PasswordResetOTP, UserActivity

OTP_LENGTH = 6
OTP_LIFETIME_MINUTES = 5
OTP_MAX_ATTEMPTS = 3


def generate_otp():
    """Cryptographically random 6-digit OTP."""
    return f"{secrets.randbelow(10 ** OTP_LENGTH):0{OTP_LENGTH}d}"


def build_reset_link(request, flow_id):
    """Absolute link to the OTP verification step for a given flow."""
    url = f"{reverse('accounts:otp_verify')}?flow={flow_id}"
    if request is not None:
        return request.build_absolute_uri(url)
    return url


def create_and_send_otp(user, request=None):
    """Create a hashed, expiring OTP for a user, email it, and log it."""
    otp = generate_otp()
    otp_obj = PasswordResetOTP.objects.create(
        user=user,
        otp_hash=make_password(otp),
        expires_at=timezone.now() + timezone.timedelta(minutes=OTP_LIFETIME_MINUTES),
    )

    link = build_reset_link(request, otp_obj.flow_id)
    subject = "Your NoteSphere password reset code"
    message = (
        f"Hello {user.full_name},\n\n"
        f"Your password reset OTP is: {otp}\n\n"
        f"It expires in {OTP_LIFETIME_MINUTES} minutes and can be used once.\n"
        f"Verify it here: {link}\n\n"
        f"If you did not request this, you can safely ignore this email."
    )
    html_message = (
        f"<p>Hello <strong>{user.full_name}</strong>,</p>"
        f"<p>Your password reset OTP is <strong>{otp}</strong>.</p>"
        f"<p>It expires in {OTP_LIFETIME_MINUTES} minutes and can be used once.</p>"
        f'<p><a href="{link}">Verify your OTP here</a></p>'
    )
    send_mail(
        subject,
        message,
        "NoteSphere <noreply@notesphere.local>",
        [user.email],
        html_message=html_message,
        fail_silently=False,
    )
    return otp_obj


def get_client_ip(request):
    if request is None:
        return None
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def parse_user_agent(user_agent):
    """Minimal, dependency-free browser/OS/device detection.

    Future-ready: swap for a dedicated parser (e.g. django-user-agents) when
    richer auditing is needed; the model fields already store the result.
    """
    ua = (user_agent or "").lower()

    if "edg/" in ua:
        browser = "Edge"
    elif "chrome/" in ua or "crios/" in ua:
        browser = "Chrome"
    elif "firefox/" in ua or "fxios/" in ua:
        browser = "Firefox"
    elif "safari/" in ua:
        browser = "Safari"
    elif "trident" in ua or "msie" in ua:
        browser = "Internet Explorer"
    else:
        browser = "Unknown"

    if "windows" in ua:
        os_name = "Windows"
    elif "android" in ua:
        os_name = "Android"
    elif "iphone" in ua or "ipad" in ua or "ios" in ua:
        os_name = "iOS"
    elif "mac os" in ua or "macintosh" in ua:
        os_name = "macOS"
    elif "linux" in ua:
        os_name = "Linux"
    else:
        os_name = "Unknown"

    if "ipad" in ua or "tablet" in ua:
        device = "Tablet"
    elif "mobile" in ua or "android" in ua or "iphone" in ua:
        device = "Mobile"
    elif "bot" in ua or "crawler" in ua or "spider" in ua:
        device = "Bot"
    else:
        device = "Desktop"

    return browser, os_name, device


def log_activity(user, action, request=None, detail=""):
    """Record an auditable action for a user."""
    user_agent = request.META.get("HTTP_USER_AGENT", "") if request is not None else ""
    browser, os_name, device = parse_user_agent(user_agent)
    return UserActivity.objects.create(
        user=user,
        action=action,
        detail=detail,
        ip_address=get_client_ip(request),
        browser=browser,
        os=os_name,
        device=device,
    )


@transaction.atomic
def set_password_and_track(user, raw_password, request=None, action=UserActivity.Action.PASSWORD_RESET, detail=""):
    """Hash and persist a new password, record when it changed, and log it."""
    user.set_password(raw_password)
    user.password_changed_at = timezone.now()
    user.save(update_fields=["password", "password_changed_at", "updated_at"])
    log_activity(user, action, request, detail)
    return user
