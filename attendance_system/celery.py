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
    # Auto clock-out check every 10 minutes
    'auto-clock-out-check': {
        'task': 'attendance.tasks.auto_clock_out_check',
        'schedule': crontab(minute='*/10'),  # Every 10 minutes
    },
    # Missed clock-out check daily at 8 PM
    'missed-clock-out-reminder': {
        'task': 'attendance.tasks.send_missed_clock_out_reminders',
        'schedule': crontab(hour=20, minute=0),  # 8 PM daily
    },
    # Weekly reports every Friday at 5 PM
    'weekly-reports': {
        'task': 'attendance.tasks.send_weekly_reports',
        'schedule': crontab(hour=17, minute=0, day_of_week=5),  # Friday 5 PM
    },
}

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
