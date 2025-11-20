#!/bin/bash
# Start Celery Beat Scheduler

source env/bin/activate
celery -A attendance_system beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
