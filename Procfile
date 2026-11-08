release: python manage.py migrate --noinput && python manage.py collectstatic --noinput
web: python manage.py collectstatic --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --timeout 120 --log-file - --access-logfile -
