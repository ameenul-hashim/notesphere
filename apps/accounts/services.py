"""Business services for the authentication module.

Keeps views thin and centralizes OTP, email, and password-change behaviour.
No per-student activity logs are stored — user data lives only on `User`.
"""

import secrets

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from .models import PasswordResetOTP

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
    _from = f"NoteSphere <{settings.EMAIL_HOST_USER}>"
    send_mail(
        subject,
        message,
        _from,
        [user.email],
        html_message=html_message,
        fail_silently=False,
    )
    return otp_obj


@transaction.atomic
def set_password_and_track(user, raw_password):
    """Hash and persist a new password and record when it changed."""
    user.set_password(raw_password)
    user.password_changed_at = timezone.now()
    user.save(update_fields=["password", "password_changed_at", "updated_at"])
    return user
