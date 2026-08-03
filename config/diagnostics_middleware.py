"""
Temporary Production Diagnostics Middleware for Railway.

Logs detailed exception tracebacks, headers, host information, and CSRF failure reasons for 400/500 requests.
"""

import sys
import logging
import traceback
from django.conf import settings
from django.core.exceptions import DisallowedHost
from django.http import HttpResponseBadRequest

logger = logging.getLogger(__name__)


class ProductionDiagnosticsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 1. Log incoming request details before standard middleware processing
        host_header = request.META.get('HTTP_HOST', '<NO_HTTP_HOST>')
        try:
            received_host = request.get_host()
        except DisallowedHost as e:
            received_host = f"<DisallowedHost: {e}>"
            self._log_diagnostics(request, e, "DisallowedHost raised in get_host()")

        response = None
        try:
            response = self.get_response(request)
        except Exception as exc:
            self._log_diagnostics(request, exc, f"Unhandled Exception ({exc.__class__.__name__})")
            raise exc

        if response is not None and response.status_code in (400, 403, 500):
            print(
                f"\n[RAILWAY DIAGNOSTICS] Response Status {response.status_code} for URL: {request.build_absolute_uri()}\n"
                f"  - HTTP_HOST header: {host_header}\n"
                f"  - request.get_host(): {received_host}\n"
                f"  - settings.ALLOWED_HOSTS: {getattr(settings, 'ALLOWED_HOSTS', [])}\n"
                f"  - settings.CSRF_TRUSTED_ORIGINS: {getattr(settings, 'CSRF_TRUSTED_ORIGINS', [])}\n",
                file=sys.stderr,
                flush=True,
            )

        return response

    def process_exception(self, request, exception):
        self._log_diagnostics(request, exception, f"process_exception caught {exception.__class__.__name__}")
        return None

    def _log_diagnostics(self, request, exception, context_msg):
        host_header = request.META.get('HTTP_HOST', '<NO_HTTP_HOST>')
        try:
            received_host = request.get_host()
        except Exception:
            received_host = "<Error retrieving host>"

        tb = "".join(traceback.format_exception(type(exception), exception, exception.__traceback__))

        log_output = (
            f"\n==================== [RAILWAY DIAGNOSTICS ERROR LOG] ====================\n"
            f"Context: {context_msg}\n"
            f"Exception Type: {exception.__class__.__module__}.{exception.__class__.__name__}\n"
            f"Exception Detail: {str(exception)}\n"
            f"Request URL: {request.build_absolute_uri()}\n"
            f"HTTP_HOST header: {host_header}\n"
            f"request.get_host(): {received_host}\n"
            f"settings.ALLOWED_HOSTS: {getattr(settings, 'ALLOWED_HOSTS', [])}\n"
            f"settings.CSRF_TRUSTED_ORIGINS: {getattr(settings, 'CSRF_TRUSTED_ORIGINS', [])}\n"
            f"Request Method: {request.method}\n"
            f"META headers:\n"
            f"  - HTTP_X_FORWARDED_HOST: {request.META.get('HTTP_X_FORWARDED_HOST', 'None')}\n"
            f"  - HTTP_X_FORWARDED_PROTO: {request.META.get('HTTP_X_FORWARDED_PROTO', 'None')}\n"
            f"  - HTTP_X_FORWARDED_FOR: {request.META.get('HTTP_X_FORWARDED_FOR', 'None')}\n"
            f"Traceback:\n{tb}"
            f"=========================================================================\n"
        )
        print(log_output, file=sys.stderr, flush=True)


def custom_csrf_failure_logger(request, reason=""):
    host_header = request.META.get('HTTP_HOST', '<NO_HTTP_HOST>')
    try:
        received_host = request.get_host()
    except Exception:
        received_host = "<Error retrieving host>"

    log_output = (
        f"\n==================== [RAILWAY DIAGNOSTICS CSRF FAILURE] ====================\n"
        f"CSRF Failure Reason: {reason}\n"
        f"Request URL: {request.build_absolute_uri()}\n"
        f"HTTP_HOST header: {host_header}\n"
        f"request.get_host(): {received_host}\n"
        f"settings.ALLOWED_HOSTS: {getattr(settings, 'ALLOWED_HOSTS', [])}\n"
        f"settings.CSRF_TRUSTED_ORIGINS: {getattr(settings, 'CSRF_TRUSTED_ORIGINS', [])}\n"
        f"Request Method: {request.method}\n"
        f"HTTP_ORIGIN: {request.META.get('HTTP_ORIGIN', 'None')}\n"
        f"HTTP_REFERER: {request.META.get('HTTP_REFERER', 'None')}\n"
        f"=============================================================================\n"
    )
    print(log_output, file=sys.stderr, flush=True)

    return HttpResponseBadRequest(
        f"<h1>400 Bad Request (CSRF Failure Diagnostics)</h1><p>Reason: {reason}</p>",
        content_type="text/html",
    )
