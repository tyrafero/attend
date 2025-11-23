#!/bin/bash

# Enable verbose debugging - show every command
set -x

echo "=== STARTING DEPLOYMENT ==="

# Show environment info
echo "PORT is: $PORT"
echo "Python version:"
python --version

echo "=== CHECKING GUNICORN ==="
which gunicorn
gunicorn --version

echo "=== RUNNING MIGRATIONS ==="
python manage.py migrate --noinput
echo "=== MIGRATIONS COMPLETE ==="

echo "=== TESTING DJANGO IMPORT ==="
python -c "import django; print('Django version:', django.get_version()); from django.conf import settings; django.setup(); print('Django setup complete')"
echo "=== DJANGO IMPORT SUCCESSFUL ==="

echo "=== STARTING GUNICORN ON PORT $PORT ==="
exec gunicorn attendance_system.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 3 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    2>&1
