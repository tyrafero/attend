# Celery Auto Start/Stop Setup

This setup will automatically start Celery workers at 5 AM and stop them at 6 PM daily, preventing memory issues and crashes during off-hours.

## Installation Steps

### 1. Copy Service Files to Systemd

```bash
sudo cp celery-worker.service /etc/systemd/system/
sudo cp celery-beat.service /etc/systemd/system/
sudo cp celery-start.service /etc/systemd/system/
sudo cp celery-start.timer /etc/systemd/system/
sudo cp celery-stop.service /etc/systemd/system/
sudo cp celery-stop.timer /etc/systemd/system/
```

### 2. Reload Systemd

```bash
sudo systemctl daemon-reload
```

### 3. Enable the Timers

```bash
# Enable timers to run on boot
sudo systemctl enable celery-start.timer
sudo systemctl enable celery-stop.timer

# Start the timers
sudo systemctl start celery-start.timer
sudo systemctl start celery-stop.timer
```

### 4. Manual Start (for testing or immediate use)

```bash
# Start services manually
sudo systemctl start celery-worker.service
sudo systemctl start celery-beat.service

# Check status
sudo systemctl status celery-worker.service
sudo systemctl status celery-beat.service
```

### 5. Manual Stop

```bash
# Stop services manually
sudo systemctl stop celery-beat.service
sudo systemctl stop celery-worker.service
```

## Schedule

- **5:00 AM**: Celery worker and beat will start automatically
- **6:00 PM**: Celery worker and beat will stop automatically

This ensures:
- No memory usage during off-hours (6 PM - 5 AM)
- No midnight crashes
- Workers are fresh every morning
- Automatic start/stop without manual intervention

## Check Timer Status

```bash
# List all timers
systemctl list-timers

# Check specific timer status
systemctl status celery-start.timer
systemctl status celery-stop.timer
```

## View Logs

```bash
# Celery worker logs
tail -f /home/vboxuser/Documents/attend/logs/celery-worker.log

# Celery beat logs
tail -f /home/vboxuser/Documents/attend/logs/celery-beat.log

# Systemd service logs
sudo journalctl -u celery-worker.service -f
sudo journalctl -u celery-beat.service -f
```

## Troubleshooting

### If services fail to start:

1. Check Redis is running:
   ```bash
   sudo systemctl status redis
   ```

2. Check permissions:
   ```bash
   sudo chown -R vboxuser:vboxuser /home/vboxuser/Documents/attend/logs
   ```

3. Test Celery manually:
   ```bash
   cd /home/vboxuser/Documents/attend
   source env/bin/activate
   celery -A attendance_system worker --loglevel=info
   ```

### Disable auto start/stop:

```bash
sudo systemctl stop celery-start.timer
sudo systemctl stop celery-stop.timer
sudo systemctl disable celery-start.timer
sudo systemctl disable celery-stop.timer
```

## Alternative: Simple Cron-Based Approach

If you prefer cron over systemd timers, add these to your crontab (`crontab -e`):

```cron
# Start Celery at 5 AM
0 5 * * * cd /home/vboxuser/Documents/attend && source env/bin/activate && celery -A attendance_system worker --detach --logfile=logs/celery-worker.log --pidfile=logs/celery-worker.pid

0 5 * * * cd /home/vboxuser/Documents/attend && source env/bin/activate && celery -A attendance_system beat --detach --logfile=logs/celery-beat.log --pidfile=logs/celery-beat.pid --scheduler django_celery_beat.schedulers:DatabaseScheduler

# Stop Celery at 6 PM
0 18 * * * pkill -f "celery.*attendance_system"
```
