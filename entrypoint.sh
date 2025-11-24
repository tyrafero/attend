#!/bin/bash
set -e  # Exit on error

echo "=== STARTING DEPLOYMENT ==="
echo "Python version: $(python --version)"

# Run migrations
echo "=== RUNNING MIGRATIONS ==="
python manage.py migrate --noinput || {
    echo "WARNING: Migrations failed, but continuing..."
}

# Verify Gunicorn is installed
echo "=== VERIFYING GUNICORN ==="
python -c "import gunicorn; print('Gunicorn version:', gunicorn.__version__)"

# Start Gunicorn on port 8000 (matches EXPOSE in Dockerfile)
echo "=== STARTING GUNICORN ON PORT 8000 ==="
exec gunicorn attendance_system.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info
