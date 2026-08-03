release: python manage.py collectstatic --noinput
web: python manage.py collectstatic --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --log-file - --access-logfile -
