#!/bin/bash

# Don't exit on error - let Django handle database issues
set +e

echo "Starting deployment..."

# Quick database check (max 5 seconds)
echo "Checking database connection..."
python << END
import sys
import time
from decouple import config

max_retries = 5
for i in range(max_retries):
    try:
        import MySQLdb
        conn = MySQLdb.connect(
            host=config('DB_HOST', default='localhost'),
            port=int(config('DB_PORT', default='3306')),
            user=config('DB_USER', default='root'),
            passwd=config('DB_PASSWORD', default=''),
            db=config('DB_NAME', default='attendance_db')
        )
        conn.close()
        print("Database ready!")
        sys.exit(0)
    except Exception as e:
        if i < max_retries - 1:
            time.sleep(1)
        else:
            print(f"Database check failed, continuing anyway: {e}")
            sys.exit(0)
END

# Run migrations (continue even if they fail)
echo "Running migrations..."
python manage.py migrate --noinput || echo "Migrations failed, continuing..."

# Start Gunicorn - this is the critical part that must succeed
echo "Starting Gunicorn on port ${PORT:-8000}..."
exec gunicorn attendance_system.wsgi:application \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers 3 \
    --timeout 120 \
    --log-level info \
    --access-logfile - \
    --error-logfile -
