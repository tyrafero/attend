#!/bin/bash
set -e  # Exit on error

echo "=== STARTING DEPLOYMENT ==="
echo "PORT: ${PORT:-8000}"
echo "Python version: $(python --version)"

# Run migrations
echo "=== RUNNING MIGRATIONS ==="
python manage.py migrate --noinput || {
    echo "WARNING: Migrations failed, but continuing..."
}

# Verify Gunicorn is installed
echo "=== VERIFYING GUNICORN ==="
python -c "import gunicorn; print('Gunicorn version:', gunicorn.__version__)"

# Start Gunicorn
echo "=== STARTING GUNICORN ON PORT ${PORT:-8000} ==="
exec gunicorn attendance_system.wsgi:application \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers 3 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info
