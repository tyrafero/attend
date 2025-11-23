#!/bin/bash

# Exit on error
set -e

echo "Starting deployment..."

# Wait for database to be ready (if needed)
echo "Waiting for database..."
python << END
import sys
import time
import os
from decouple import config

max_retries = 30
retry_count = 0

while retry_count < max_retries:
    try:
        import MySQLdb
        db_host = config('DB_HOST', default='localhost')
        db_port = int(config('DB_PORT', default='3306'))
        db_user = config('DB_USER', default='root')
        db_password = config('DB_PASSWORD', default='')
        db_name = config('DB_NAME', default='attendance_db')

        print(f"Attempting to connect to {db_host}:{db_port}...")
        conn = MySQLdb.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            passwd=db_password,
            db=db_name
        )
        conn.close()
        print("Database is ready!")
        sys.exit(0)
    except Exception as e:
        retry_count += 1
        print(f"Database not ready (attempt {retry_count}/{max_retries}): {e}")
        time.sleep(2)

print("Database connection failed after maximum retries")
sys.exit(1)
END

# Run migrations
echo "Running migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

# Start Gunicorn
echo "Starting Gunicorn..."
exec gunicorn attendance_system.wsgi:application \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers 3 \
    --timeout 120 \
    --log-level warning \
    --access-logfile - \
    --error-logfile -
