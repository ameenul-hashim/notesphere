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
import socket
import ssl
import traceback
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


def _mask_key(key):
    """Mask API key for logging — show first 8 and last 4 chars."""
    if not key or len(key) < 16:
        return "***NOT_SET***"
    return f"{key[:8]}...{key[-4:]}"


def _log_env_diagnostics():
    """Log all email-related env vars at runtime (secrets masked)."""
    api_key = getattr(settings, "BREVO_API_KEY", "") or ""
    smtp_user = getattr(settings, "EMAIL_HOST_USER", "") or ""
    smtp_pass = getattr(settings, "EMAIL_HOST_PASSWORD", "") or ""
    from_email = getattr(settings, "BREVO_FROM_EMAIL", "") or ""
    from_name = getattr(settings, "BREVO_FROM_NAME", "") or ""
    support_email = getattr(settings, "SUPPORT_EMAIL", "") or ""
    django_env = getattr(settings, "DJANGO_ENV", "unknown") or "unknown"
    settings_module = getattr(settings, "SETTINGS_MODULE", "unknown") or "unknown"

    # Try to get the actual settings module from env
    import os
    settings_module = os.environ.get("DJANGO_SETTINGS_MODULE", "unknown")

    logger.info("=" * 60)
    logger.info("EMAIL ENVIRONMENT DIAGNOSTICS")
    logger.info("=" * 60)
    logger.info("DJANGO_ENV              = %s", django_env)
    logger.info("SETTINGS_MODULE        = %s", settings_module)
    logger.info("BREVO_API_KEY           = %s", "SET" if api_key else "NOT SET")
    logger.info("BREVO_API_KEY (masked)  = %s", _mask_key(api_key))
    logger.info("BREVO_FROM_NAME         = %s", from_name or "(empty)")
    logger.info("BREVO_FROM_EMAIL        = %s", from_email or "(empty)")
    logger.info("SUPPORT_EMAIL           = %s", support_email or "(empty)")
    logger.info("EMAIL_BACKEND           = %s", getattr(settings, "EMAIL_BACKEND", "unknown"))
    logger.info("EMAIL_HOST              = %s", getattr(settings, "EMAIL_HOST", "unknown"))
    logger.info("EMAIL_PORT              = %s", getattr(settings, "EMAIL_PORT", "unknown"))
    logger.info("EMAIL_HOST_USER         = %s", smtp_user or "(empty)")
    logger.info("EMAIL_HOST_PASSWORD     = %s", "SET" if smtp_pass else "NOT SET")
    logger.info("EMAIL_USE_TLS           = %s", getattr(settings, "EMAIL_USE_TLS", "unknown"))
    logger.info("EMAIL_USE_SSL           = %s", getattr(settings, "EMAIL_USE_SSL", "unknown"))
    logger.info("=" * 60)


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

    # Run env diagnostics on every call (will repeat but ensures visibility)
    _log_env_diagnostics()

    api_key = getattr(settings, "BREVO_API_KEY", "") or ""

    logger.info("EMAIL PATH DECISION: api_key=%s -> %s",
                "SET" if api_key else "NOT SET",
                "Brevo HTTP API" if api_key else "SMTP fallback")

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
        reply_email = reply_to[0] if isinstance(reply_to, list) else reply_to
        payload["replyTo"] = {"email": reply_email}

    payload_json = json.dumps(payload, indent=2)

    logger.info("=" * 60)
    logger.info("BREVO HTTP API - SENDING EMAIL")
    logger.info("=" * 60)
    logger.info("URL             = https://api.brevo.com/v3/smtp/email")
    logger.info("Method          = POST")
    logger.info("API Key         = %s", _mask_key(api_key))
    logger.info("Sender Name     = %s", from_name)
    logger.info("Sender Email    = %s", from_email)
    logger.info("Recipients      = %s", to)
    logger.info("Subject         = %s", subject)
    logger.info("Reply-To        = %s", reply_to or "(none)")
    logger.info("Has HTML        = %s", bool(html_body))
    logger.info("Text Length     = %d chars", len(text_body))
    logger.info("HTML Length     = %d chars", len(html_body) if html_body else 0)
    logger.info("Payload Size    = %d bytes", len(payload_json.encode("utf-8")))
    logger.info("Payload (masked)= sender=%s/%s to=%s subject=%s",
                from_name, from_email, to, subject)
    logger.info("-" * 60)

    data = payload_json.encode("utf-8")
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
        logger.info("HTTP Request sent, waiting for response (timeout=15s)...")
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            logger.info("-" * 60)
            logger.info("BREVO API RESPONSE - SUCCESS")
            logger.info("HTTP Status     = %d", resp.status)
            logger.info("Response Headers= %s", dict(resp.headers))
            logger.info("Response Body   = %s", body)
            logger.info("Result          = %s", "ACCEPTED" if resp.status in (200, 201, 202) else "REJECTED")
            logger.info("=" * 60)
            return resp.status in (200, 201, 202)

    except urllib.error.HTTPError as exc:
        err_body = ""
        try:
            err_body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        logger.error("=" * 60)
        logger.error("BREVO API RESPONSE - HTTP ERROR")
        logger.error("HTTP Status     = %d", exc.code)
        logger.error("Response Headers= %s", dict(exc.headers) if exc.headers else "(none)")
        logger.error("Response Body   = %s", err_body)
        logger.error("Reason          = %s", exc.reason)
        # Try to parse Brevo's error JSON
        try:
            err_json = json.loads(err_body)
            logger.error("Brevo Error Code= %s", err_json.get("code", "unknown"))
            logger.error("Brevo Error Msg = %s", err_json.get("message", "unknown"))
        except (json.JSONDecodeError, ValueError):
            logger.error("Could not parse Brevo error as JSON")
        logger.error("=" * 60)
        return False

    except urllib.error.URLError as exc:
        logger.error("=" * 60)
        logger.error("BREVO API - URL ERROR (network/DNS issue)")
        logger.error("Error           = %s", exc.reason)
        logger.error("Full Traceback  = %s", traceback.format_exc())
        logger.error("=" * 60)
        return False

    except TimeoutError or socket.timeout:
        logger.error("=" * 60)
        logger.error("BREVO API - TIMEOUT")
        logger.error("Could not connect to api.brevo.com:443 within 15 seconds")
        logger.error("Full Traceback  = %s", traceback.format_exc())
        logger.error("=" * 60)
        return False

    except ssl.SSLError as exc:
        logger.error("=" * 60)
        logger.error("BREVO API - SSL ERROR")
        logger.error("Error           = %s", exc)
        logger.error("Full Traceback  = %s", traceback.format_exc())
        logger.error("=" * 60)
        return False

    except json.JSONDecodeError as exc:
        logger.error("=" * 60)
        logger.error("BREVO API - JSON DECODE ERROR")
        logger.error("Error           = %s", exc)
        logger.error("Full Traceback  = %s", traceback.format_exc())
        logger.error("=" * 60)
        return False

    except Exception as exc:
        logger.error("=" * 60)
        logger.error("BREVO API - UNEXPECTED EXCEPTION")
        logger.error("Exception Type  = %s", type(exc).__name__)
        logger.error("Exception Value = %s", exc)
        logger.error("Full Traceback  = %s", traceback.format_exc())
        logger.error("=" * 60)
        return False


def _send_via_smtp(to, subject, text_body, html_body, reply_to):
    """Fallback: send email via Django SMTP (works in local dev)."""
    from django.core.mail import EmailMessage, get_connection

    from_name  = getattr(settings, "BREVO_FROM_NAME",  "NoteSphere").strip()
    from_email = getattr(settings, "BREVO_FROM_EMAIL", settings.EMAIL_HOST_USER).strip() or "noreply@notesphere.com"
    from_addr  = f"{from_name} <{from_email}>"

    logger.info("=" * 60)
    logger.info("SMTP - SENDING EMAIL (fallback)")
    logger.info("=" * 60)
    logger.info("Host            = %s", getattr(settings, "EMAIL_HOST", "unknown"))
    logger.info("Port            = %s", getattr(settings, "EMAIL_PORT", "unknown"))
    logger.info("Username        = %s", getattr(settings, "EMAIL_HOST_USER", "(empty)"))
    logger.info("Password        = %s", "SET" if getattr(settings, "EMAIL_HOST_PASSWORD", "") else "NOT SET")
    logger.info("Use TLS         = %s", getattr(settings, "EMAIL_USE_TLS", "unknown"))
    logger.info("Use SSL         = %s", getattr(settings, "EMAIL_USE_SSL", "unknown"))
    logger.info("Backend         = %s", getattr(settings, "EMAIL_BACKEND", "unknown"))
    logger.info("From            = %s", from_addr)
    logger.info("To              = %s", to)
    logger.info("Subject         = %s", subject)
    logger.info("Reply-To        = %s", reply_to or "(none)")
    logger.info("-" * 60)

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
        logger.info("SMTP RESULT     = sent=%d %s", sent, "SUCCESS" if sent > 0 else "FAILED")
        logger.info("=" * 60)
        return sent > 0
    except Exception as exc:
        logger.error("=" * 60)
        logger.error("SMTP - FAILED")
        logger.error("Exception Type  = %s", type(exc).__name__)
        logger.error("Exception Value = %s", exc)
        logger.error("Full Traceback  = %s", traceback.format_exc())
        logger.error("=" * 60)
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

    logger.info("OTP CREATE | user=%s | flow_id=%s", user.username, otp_obj.flow_id)

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

    logger.info("OTP EMAIL RESULT | user=%s | sent=%s", user.username, sent)

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
