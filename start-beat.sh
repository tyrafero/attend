#!/bin/bash

echo "=== STARTING CELERY BEAT (SCHEDULER) ==="
echo "Current time: $(date)"

# Wait a bit for migrations to complete
sleep 5

# Start Celery beat with code-based schedule
exec celery -A attendance_system beat \
    --loglevel=info
