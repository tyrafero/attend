web: python manage.py migrate --noinput && python manage.py collectstatic --noinput --clear && gunicorn attendance_system.wsgi:application --bind 0.0.0.0:$PORT --workers 3 --timeout 120 --log-level warning --access-logfile - --error-logfile -
worker: celery -A attendance_system worker --loglevel=warning
beat: celery -A attendance_system beat --loglevel=warning --scheduler django_celery_beat.schedulers:DatabaseScheduler
