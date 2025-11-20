web: python manage.py migrate && gunicorn attendance_system.wsgi:application --bind 0.0.0.0:$PORT --workers 3 --log-level warning
worker: celery -A attendance_system worker --loglevel=warning
beat: celery -A attendance_system beat --loglevel=warning --scheduler django_celery_beat.schedulers:DatabaseScheduler
