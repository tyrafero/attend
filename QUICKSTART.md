# Quick Start Guide

## Prerequisites Check

Before starting, ensure you have:

1. ✅ MySQL server running
2. ✅ Redis server running
3. ✅ Database `attendance_db` created with proper permissions
4. ✅ Migrations applied (already done)

## Starting the Application

You need to run **3 separate terminals** for the complete system:

### Terminal 1: Django Development Server

```bash
./start_django.sh
```

Or manually:
```bash
source env/bin/activate
python manage.py runserver
```

The application will be available at: **http://localhost:8000**

### Terminal 2: Celery Worker

```bash
./start_celery_worker.sh
```

Or manually:
```bash
source env/bin/activate
celery -A attendance_system worker --loglevel=info
```

This processes background tasks like sending emails.

### Terminal 3: Celery Beat Scheduler

```bash
./start_celery_beat.sh
```

Or manually:
```bash
source env/bin/activate
celery -A attendance_system beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

This runs scheduled tasks (auto clock-out, reminders, weekly reports).

## First Time Setup

### 1. Create Superuser (Admin Account)

```bash
source env/bin/activate
python manage.py createsuperuser
```

Follow the prompts to create your admin account.

### 2. Add Your First Employee

Visit: **http://localhost:8000/admin/employees/add/**

Fill in:
- Employee ID: EMP001 (or use auto-suggested)
- Employee Name: Your Name
- Email: your.email@example.com
- PIN Code: 1234 (or any 4-6 digit PIN)

## Testing the System

### Test Employee Clock In/Out

1. Go to **http://localhost:8000/**
2. Enter the PIN you created (e.g., 1234)
3. Click "Clock In/Out"
4. You should see a success screen with your name
5. Wait 3 seconds for auto-redirect
6. Enter PIN again to clock out

### View Admin Dashboard

1. Go to **http://localhost:8000/admin/dashboard/**
2. You'll see statistics and employee status
3. Dashboard auto-refreshes every 30 seconds

### Access Django Admin Panel

1. Go to **http://localhost:8000/django-admin/**
2. Login with your superuser credentials
3. You can view all models and data

## Verify Services

### Check Redis

```bash
redis-cli ping
```

Should return: `PONG`

If Redis is not running:
```bash
redis-server
```

### Check MySQL

```bash
mysql -u stock_user -p
```

Enter password: `aashutosh1`

Then check database:
```sql
USE attendance_db;
SHOW TABLES;
```

You should see tables like:
- attendance_employeeregistry
- attendance_attendancetap
- attendance_dailysummary
- etc.

## URL Overview

| URL | Description |
|-----|-------------|
| http://localhost:8000/ | Employee Welcome Screen (PIN Entry) |
| http://localhost:8000/admin/dashboard/ | Admin Dashboard |
| http://localhost:8000/admin/employees/add/ | Add New Employee |
| http://localhost:8000/django-admin/ | Django Admin Panel |

## Common Issues

### Issue: Cannot connect to database
**Solution:** Check MySQL credentials in `attendance_system/settings.py` and ensure database exists

### Issue: Celery not running tasks
**Solution:** Make sure both Celery worker AND beat scheduler are running

### Issue: Redis connection refused
**Solution:** Start Redis server with `redis-server`

### Issue: Port 8000 already in use
**Solution:** Run Django on a different port:
```bash
python manage.py runserver 8001
```

## Testing Background Tasks

### Test Auto Clock-Out

1. Clock in an employee
2. The system will auto clock-out after 8 hours OR at 5 PM
3. Check Celery worker logs to see the task execution

### Test Email Notifications

Emails are configured to print to console in development mode.

Check the Django server terminal to see email output when:
- Employee clocks out early (< 8 hours)
- Auto clock-out happens
- Missed clock-out reminder (8 PM)
- Weekly reports (Friday 5 PM)

To use real emails, update settings in `attendance_system/settings.py`:

```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'
```

## Development Tips

- **Auto-refresh Dashboard:** The admin dashboard automatically refreshes every 30 seconds
- **Keyboard Support:** PIN entry supports keyboard (0-9, Enter, Backspace, Escape)
- **Celery Beat Schedule:** Check/modify schedules in `attendance_system/celery.py`
- **Business Rules:** Modify in `attendance/views.py` and `attendance/tasks.py`

## Next Steps

1. ✅ Create superuser
2. ✅ Add test employees
3. ✅ Test clock in/out
4. ✅ View admin dashboard
5. ✅ Test all features
6. Configure email settings for production
7. Set up proper timezone if needed
8. Customize business rules as needed

## Support

For issues, check:
1. Django server logs (Terminal 1)
2. Celery worker logs (Terminal 2)
3. Celery beat logs (Terminal 3)
4. Django admin error logs at http://localhost:8000/django-admin/

Happy attendance tracking! 🎉
