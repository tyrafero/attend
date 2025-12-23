#!/bin/bash

echo "=== Setting up Celery Services ==="

# Copy service files to systemd
sudo cp celery-worker.service /etc/systemd/system/
sudo cp celery-beat.service /etc/systemd/system/

# Reload systemd to recognize new services
sudo systemctl daemon-reload

# Enable services to start on boot
sudo systemctl enable celery-worker.service
sudo systemctl enable celery-beat.service

# Start services
sudo systemctl start celery-worker.service
sudo systemctl start celery-beat.service

# Check status
echo ""
echo "=== Celery Worker Status ==="
sudo systemctl status celery-worker.service --no-pager

echo ""
echo "=== Celery Beat Status ==="
sudo systemctl status celery-beat.service --no-pager

echo ""
echo "=== Setup Complete! ==="
echo "Worker logs: sudo journalctl -u celery-worker.service -f"
echo "Beat logs: sudo journalctl -u celery-beat.service -f"
