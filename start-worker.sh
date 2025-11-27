#!/bin/bash

echo "=== STARTING CELERY WORKER ==="
echo "Current time: $(date)"

# Run migrations (safe to run multiple times)
python manage.py migrate --noinput

# Start Celery worker
exec celery -A attendance_system worker \
    --loglevel=info \
    --concurrency=2 \
    --max-tasks-per-child=100
