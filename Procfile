web: python manage.py migrate && gunicorn attendance_system.wsgi:application --bind 0.0.0.0:$PORT --workers 3
worker: celery -A attendance_system worker --loglevel=info
beat: celery -A attendance_system beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
