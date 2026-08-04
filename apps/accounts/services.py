"""Business services for the authentication module.

Keeps views thin and centralises OTP, email, and password-change behaviour.

Email provider: Brevo HTTP API (https://api.brevo.com/v3/smtp/email)
All transactional mail goes through send_transactional_email() — the single
entry point for every email in the application.

Falls back to Django SMTP if BREVO_API_KEY is not set (local development).
"""

import json
import logging
import secrets
import urllib.request
import urllib.error

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from .models import PasswordResetOTP

logger = logging.getLogger(__name__)

OTP_LENGTH = 6
OTP_LIFETIME_MINUTES = 5
OTP_MAX_ATTEMPTS = 3


# ---------------------------------------------------------------------------
# Unified transactional email helper — Brevo HTTP API
# ---------------------------------------------------------------------------

def send_transactional_email(to, subject, text_body, html_body=None, reply_to=None):
    """Send one transactional email via Brevo HTTP API.

    Uses https://api.brevo.com/v3/smtp/email (port 443) which is not
    blocked by Railway's outbound firewall (SMTP port 587 is blocked).

    Falls back to Django SMTP if BREVO_API_KEY is not configured.

    Args:
        to          : recipient address (str) or list of addresses.
        subject     : email subject line.
        text_body   : plain-text fallback body.
        html_body   : optional HTML body.
        reply_to    : optional Reply-To address string or list.

    Returns:
        True on success, False on failure (exception is logged).
    """
    if isinstance(to, str):
        to = [to]
    if isinstance(reply_to, str):
        reply_to = [reply_to]

    api_key = getattr(settings, "BREVO_API_KEY", "") or ""
    if api_key:
        return _send_via_brevo_api(api_key, to, subject, text_body, html_body, reply_to)
    else:
        return _send_via_smtp(to, subject, text_body, html_body, reply_to)


def _send_via_brevo_api(api_key, to, subject, text_body, html_body, reply_to):
    """Send email using Brevo's transactional HTTP API."""
    from_name  = getattr(settings, "BREVO_FROM_NAME",  "NoteSphere").strip()
    from_email = getattr(settings, "BREVO_FROM_EMAIL", "noreply@notesphere.com").strip()

    payload = {
        "sender": {"name": from_name, "email": from_email},
        "to": [{"email": addr} for addr in to],
        "subject": subject,
        "textContent": text_body,
    }
    if html_body:
        payload["htmlContent"] = html_body
    if reply_to:
        payload["replyTo"] = [{"email": reply_to[0] if isinstance(reply_to, list) else reply_to}]

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://api.brevo.com/v3/smtp/email",
        data=data,
        headers={
            "accept": "application/json",
            "api-key": api_key,
            "content-type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            logger.info("Email sent via Brevo API | to=%s | subject=%s | status=%s", to, subject, resp.status)
            return resp.status in (200, 201, 202)
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        logger.error("Brevo API HTTP %s | to=%s | subject=%s | response=%s", exc.code, to, subject, err_body)
        return False
    except Exception as exc:
        logger.exception("Brevo API FAILED | to=%s | subject=%s | error=%s", to, subject, exc)
        return False


def _send_via_smtp(to, subject, text_body, html_body, reply_to):
    """Fallback: send email via Django SMTP (works in local dev)."""
    from django.core.mail import EmailMessage, get_connection
    import socket

    from_name  = getattr(settings, "BREVO_FROM_NAME",  "NoteSphere").strip()
    from_email = getattr(settings, "BREVO_FROM_EMAIL", settings.EMAIL_HOST_USER).strip() or "noreply@notesphere.com"
    from_addr  = f"{from_name} <{from_email}>"

    old_timeout = socket.getdefaulttimeout()
    try:
        socket.setdefaulttimeout(15)
        connection = get_connection(
            backend  = settings.EMAIL_BACKEND,
            host     = settings.EMAIL_HOST,
            port     = settings.EMAIL_PORT,
            username = settings.EMAIL_HOST_USER,
            password = settings.EMAIL_HOST_PASSWORD,
            use_tls  = settings.EMAIL_USE_TLS,
            use_ssl  = settings.EMAIL_USE_SSL,
        )
        msg = EmailMessage(
            subject    = subject,
            body       = text_body,
            from_email = from_addr,
            to         = to,
            reply_to   = reply_to or [],
            connection = connection,
        )
        if html_body:
            msg.content_subtype = "html"
            msg.body = html_body
        sent = msg.send(fail_silently=False)
        logger.info("Email sent via SMTP | to=%s | subject=%s | accepted=%s", to, subject, sent)
        return sent > 0
    except Exception as exc:
        logger.exception("SMTP FAILED | to=%s | subject=%s | error=%s", to, subject, exc)
        return False
    finally:
        socket.setdefaulttimeout(old_timeout)


# ---------------------------------------------------------------------------
# OTP / password-reset flow
# ---------------------------------------------------------------------------

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
    """Create a hashed, expiring OTP for a user and email it via Brevo."""
    otp = generate_otp()
    otp_obj = PasswordResetOTP.objects.create(
        user      = user,
        otp_hash  = make_password(otp),
        expires_at= timezone.now() + timezone.timedelta(minutes=OTP_LIFETIME_MINUTES),
    )

    link = build_reset_link(request, otp_obj.flow_id)

    text_body = (
        f"Hello {user.full_name},\n\n"
        f"Your NoteSphere password reset OTP is: {otp}\n\n"
        f"It expires in {OTP_LIFETIME_MINUTES} minutes and can only be used once.\n"
        f"Verify here: {link}\n\n"
        f"If you did not request this, you can safely ignore this email.\n\n"
        f"— The NoteSphere Team"
    )
    html_body = f"""
<div style="font-family:Arial,sans-serif;max-width:480px;margin:0 auto;padding:24px;background:#fff;border:1px solid #e5e7eb;border-radius:8px;">
  <h2 style="color:#111827;margin-top:0;">Password Reset OTP</h2>
  <p style="color:#374151;">Hello <strong>{user.full_name}</strong>,</p>
  <p style="color:#374151;">Use the OTP below to reset your password.</p>
  <div style="background:#f3f4f6;border-radius:8px;padding:20px;text-align:center;margin:20px 0;">
    <span style="font-size:36px;font-weight:700;letter-spacing:8px;color:#6366f1;">{otp}</span>
  </div>
  <p style="color:#6b7280;font-size:13px;">
    Valid for <strong>{OTP_LIFETIME_MINUTES} minutes</strong>. One-time use only.
  </p>
  <a href="{link}" style="display:inline-block;background:#6366f1;color:#fff;padding:12px 24px;border-radius:6px;text-decoration:none;font-weight:600;margin-top:8px;">
    Verify OTP
  </a>
  <p style="color:#9ca3af;font-size:12px;margin-top:24px;">
    If you did not request this, ignore this email — your account is safe.
  </p>
</div>
"""

    sent = send_transactional_email(
        to       = user.email,
        subject  = "Your NoteSphere Password Reset OTP",
        text_body= text_body,
        html_body= html_body,
    )

    if not sent:
        logger.error("OTP email failed to send for user %s (%s)", user.username, user.email)

    return otp_obj


# ---------------------------------------------------------------------------
# Password change
# ---------------------------------------------------------------------------

@transaction.atomic
def set_password_and_track(user, raw_password):
    """Hash and persist a new password and record when it changed."""
    user.set_password(raw_password)
    user.password_changed_at = timezone.now()
    user.save(update_fields=["password", "password_changed_at", "updated_at"])
    return user
