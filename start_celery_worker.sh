#!/bin/bash
# Start Celery Worker

source env/bin/activate
celery -A attendance_system worker --loglevel=info
