#!/bin/bash

echo "=== STARTING CELERY BEAT (SCHEDULER) ==="
echo "Current time: $(date)"

# Run migrations (safe to run multiple times)
python manage.py migrate --noinput

# Start Celery beat
exec celery -A attendance_system beat \
    --loglevel=info
