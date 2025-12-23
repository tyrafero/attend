#!/bin/bash

echo "=== Checking Scheduled Tasks ==="
echo ""

cd /home/vboxuser/Documents/attend
source env/bin/activate

echo "1. Celery Beat Service Status:"
sudo systemctl is-active celery-beat.service && echo "✅ Beat is running" || echo "❌ Beat is NOT running"

echo ""
echo "2. Scheduled Tasks in Celery:"
celery -A attendance_system inspect scheduled

echo ""
echo "3. Celery Beat Schedule Configuration:"
python manage.py shell << 'PYTHON'
from attendance_system.celery import app

print("Configured scheduled tasks:")
for task_name, task_config in app.conf.beat_schedule.items():
    print(f"\n  📅 {task_name}:")
    print(f"     Task: {task_config['task']}")
    print(f"     Schedule: {task_config['schedule']}")
PYTHON

echo ""
echo "4. Recent Beat Logs:"
sudo journalctl -u celery-beat.service -n 20 --no-pager | grep -i "auto-clock\|weekly"
