import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'attendance_system.settings')

app = Celery('attendance_system')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery Beat schedule
app.conf.beat_schedule = {
    # Auto clock-out check every 30 minutes (no email notification)
    'auto-clock-out-check': {
        'task': 'attendance.tasks.auto_clock_out_check',
        'schedule': crontab(minute='*/30'),  # Every 30 minutes
    },
    # Weekly reports every Friday at 5 PM (beautiful HTML emails)
    'weekly-reports': {
        'task': 'attendance.tasks.send_weekly_reports',
        'schedule': crontab(hour=17, minute=0, day_of_week=5),  # Friday 5 PM
    },
    # Disabled email notifications (only weekly reports are sent):
    # - Missed clock-out reminders (disabled)
    # - Auto clock-out notifications (disabled in tasks.py)
    # - Early clock-out alerts (disabled)
}

# Set timezone for beat scheduler
app.conf.timezone = 'Australia/Sydney'

# Additional Celery configuration
app.conf.update(
    worker_max_tasks_per_child=100,  # Reduced to prevent memory issues
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
