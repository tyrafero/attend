#!/bin/bash

echo "=== Celery Services Status ==="
echo ""

echo "📊 Redis:"
redis-cli ping && echo "✅ Redis is running" || echo "❌ Redis is NOT running"

echo ""
echo "👷 Celery Worker:"
sudo systemctl is-active celery-worker.service && echo "✅ Worker is running" || echo "❌ Worker is NOT running"

echo ""
echo "⏰ Celery Beat:"
sudo systemctl is-active celery-beat.service && echo "✅ Beat is running" || echo "❌ Beat is NOT running"

echo ""
echo "=== Active Celery Tasks ==="
cd /home/vboxuser/Documents/attend
source env/bin/activate
celery -A attendance_system inspect active

echo ""
echo "=== Scheduled Tasks ==="
celery -A attendance_system inspect scheduled

echo ""
echo "=== Recent Worker Logs (last 20 lines) ==="
sudo journalctl -u celery-worker.service -n 20 --no-pager

echo ""
echo "=== Recent Beat Logs (last 20 lines) ==="
sudo journalctl -u celery-beat.service -n 20 --no-pager
