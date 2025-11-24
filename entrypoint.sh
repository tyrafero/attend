#!/bin/bash

echo "=== ENTRYPOINT SCRIPT STARTED ==="
echo "Script location: $(pwd)"
echo "Files in current directory:"
ls -la

# Don't exit on error yet - we want to see what fails
set +e

echo ""
echo "=== CHECKING ENVIRONMENT ==="
echo "PORT: ${PORT:-not set}"
echo "DEBUG: ${DEBUG:-not set}"
echo "PYTHONPATH: ${PYTHONPATH:-not set}"

echo ""
echo "=== CHECKING PYTHON ==="
which python
python --version
echo "Python executable: $(which python)"

echo ""
echo "=== CHECKING DJANGO FILES ==="
ls -la manage.py || echo "ERROR: manage.py not found!"
ls -la attendance_system/ || echo "ERROR: attendance_system directory not found!"

echo ""
echo "=== TESTING PYTHON IMPORTS ==="
python -c "import sys; print('Python path:', sys.path)" || echo "ERROR: Failed to run python"
python -c "import django; print('Django imported OK, version:', django.__version__)" || echo "ERROR: Failed to import Django"
python -c "import MySQLdb; print('MySQLdb imported OK')" || echo "ERROR: Failed to import MySQLdb"

echo ""
echo "=== CHECKING ENVIRONMENT VARIABLES ==="
python -c "from decouple import config; print('DB_HOST:', config('DB_HOST', default='NOT SET'))" || echo "ERROR: Failed to read config"

echo ""
echo "=== TESTING DJANGO SETTINGS ==="
python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'attendance_system.settings')
import django
print('About to call django.setup()...')
django.setup()
print('Django setup successful!')
" || echo "ERROR: Django setup failed!"

echo ""
echo "=== RUNNING MIGRATIONS ==="
python manage.py migrate --noinput && echo "Migrations completed successfully" || {
    echo "WARNING: Migrations failed with exit code $?"
    echo "Continuing anyway..."
}

echo ""
echo "=== VERIFYING GUNICORN ==="
which gunicorn || echo "ERROR: gunicorn not found in PATH"
python -c "import gunicorn; print('Gunicorn version:', gunicorn.__version__)" || echo "ERROR: Failed to import gunicorn"

echo ""
echo "=== TESTING WSGI APPLICATION ==="
python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'attendance_system.settings')
from attendance_system.wsgi import application
print('WSGI application imported successfully!')
print('Application object:', application)
" || echo "ERROR: Failed to import WSGI application!"

echo ""
echo "=== ABOUT TO START GUNICORN ==="
echo "Command: gunicorn attendance_system.wsgi:application --bind 0.0.0.0:8000"
echo "Current time: $(date)"

# Now enable exit on error for gunicorn
set -e

echo ""
echo "=== EXECUTING GUNICORN NOW ==="
exec gunicorn attendance_system.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level debug \
    --capture-output
