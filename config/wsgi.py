"""
WSGI config for NoteSphere project.

Includes low-level WSGI startup diagnostics and request logger wrapper to capture
400 Bad Request errors before Django middleware processing.
"""

import os
import sys
from django.core.wsgi import get_wsgi_application

print("\n==================== [WSGI STARTUP DIAGNOSTICS] ====================", file=sys.stderr, flush=True)
print(f"DJANGO_SETTINGS_MODULE (env): {os.environ.get('DJANGO_SETTINGS_MODULE', '<not set>')}", file=sys.stderr, flush=True)
print(f"DJANGO_ENV (env): {os.environ.get('DJANGO_ENV', '<not set>')}", file=sys.stderr, flush=True)
print(f"DJANGO_ALLOWED_HOSTS (raw env): '{os.environ.get('DJANGO_ALLOWED_HOSTS', '<not set>')}'", file=sys.stderr, flush=True)

# Set default settings module if not already set by environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

django_app = get_wsgi_application()

from django.conf import settings

print(f"Active Settings Module: {settings.SETTINGS_MODULE}", file=sys.stderr, flush=True)
print(f"Resolved ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}", file=sys.stderr, flush=True)
print(f"Using production.py?: {'production' in settings.SETTINGS_MODULE}", file=sys.stderr, flush=True)
print(f"Using base.py?: {'base' in settings.SETTINGS_MODULE}", file=sys.stderr, flush=True)
print(f"Middleware List: {settings.MIDDLEWARE}", file=sys.stderr, flush=True)
print("====================================================================\n", file=sys.stderr, flush=True)


class WSGIStartupLogger:
    """WSGI middleware wrapper to catch 400 Bad Request at the lowest WSGI entrypoint."""

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        http_host = environ.get('HTTP_HOST', '<NO_HTTP_HOST>')
        x_forwarded_host = environ.get('HTTP_X_FORWARDED_HOST', '<NONE>')
        x_forwarded_proto = environ.get('HTTP_X_FORWARDED_PROTO', '<NONE>')
        request_uri = environ.get('PATH_INFO', '/')

        print(
            f"[WSGI REQUEST ENTERING] URI: {request_uri} | HTTP_HOST: {http_host} | "
            f"X-Forwarded-Host: {x_forwarded_host} | X-Forwarded-Proto: {x_forwarded_proto}",
            file=sys.stderr,
            flush=True,
        )

        def custom_start_response(status, headers, exc_info=None):
            if status.startswith("400") or status.startswith("500"):
                print(
                    f"\n[WSGI RESPONSE ERROR DETECTED]\n"
                    f"  - Status: {status}\n"
                    f"  - Request URI: {request_uri}\n"
                    f"  - HTTP_HOST: {http_host}\n"
                    f"  - X-Forwarded-Host: {x_forwarded_host}\n"
                    f"  - X-Forwarded-Proto: {x_forwarded_proto}\n"
                    f"  - settings.ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}\n"
                    f"  - settings.SETTINGS_MODULE: {settings.SETTINGS_MODULE}\n",
                    file=sys.stderr,
                    flush=True,
                )
                if exc_info:
                    import traceback
                    print("".join(traceback.format_exception(*exc_info)), file=sys.stderr, flush=True)

            return start_response(status, headers, exc_info)

        try:
            return self.app(environ, custom_start_response)
        except Exception as exc:
            import traceback
            print(f"\n[WSGI UNHANDLED EXCEPTION AT ENTRYPOINT] {exc.__class__.__name__}: {exc}", file=sys.stderr, flush=True)
            print(traceback.format_exc(), file=sys.stderr, flush=True)
            raise exc


application = WSGIStartupLogger(django_app)
