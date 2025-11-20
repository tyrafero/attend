# PIN-Based Employee Attendance System

A comprehensive Django-based attendance tracking system with PIN authentication, automatic clock-out, email notifications, and admin dashboard.

## Features

### Core Functionality
- **PIN-Based Authentication**: Employees clock in/out using a 4-6 digit PIN
- **Automatic IN/OUT Detection**: System determines if it's clock IN or OUT based on tap count
- **Beautiful Success Screen**: Shows employee name, action, time, and hours worked
- **Auto-Redirect**: Returns to welcome screen after 3 seconds

### Business Rules
- Required shift: 8 hours (including break)
- Automatic 30-minute lunch deduction for shifts > 5 hours
- Clock in/out restricted to 7 AM - 5 PM (Australia/Sydney timezone)
- Auto clock-out after 8 hours OR at 5 PM (whichever comes first)

### Admin Features
- Dashboard with real-time statistics
- Employee management
- Daily summaries with hours tracking
- Audit log for timesheet edits
- Email notification logs

### Email Notifications
- **Early Clock-Out Alert**: Sent when employee clocks out before 8 hours
- **Missed Clock-Out Reminder**: Daily at 8 PM for employees still clocked IN
- **Weekly Reports**: Every Friday at 5 PM (individual reports + manager summary)

### Background Tasks (Celery)
- Auto clock-out check every 10 minutes
- Missed clock-out check daily at 8 PM
- Weekly report generation on Fridays at 5 PM

## Installation & Setup

### 1. Prerequisites

Make sure you have:
- Python 3.12+
- MySQL Server
- Redis Server (for Celery)

### 2. Database Setup

Create the MySQL database:

```sql
CREATE DATABASE attendance_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Update database credentials in `attendance_system/settings.py`:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'attendance_db',
        'USER': 'your_username',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '3306',
    }
}
```

### 3. Install Dependencies

The virtual environment is already set up. Activate it and dependencies are installed:

```bash
source env/bin/activate
```

### 4. Run Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Create Superuser

```bash
python manage.py createsuperuser
```

### 6. Email Configuration (Optional)

For production, update email settings in `attendance_system/settings.py`:

```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'
DEFAULT_FROM_EMAIL = 'your-email@gmail.com'
```

For development, emails will print to console.

### 7. Start Redis Server

```bash
redis-server
```

### 8. Start Celery Worker

In a new terminal:

```bash
source env/bin/activate
celery -A attendance_system worker --loglevel=info
```

### 9. Start Celery Beat (Scheduler)

In another new terminal:

```bash
source env/bin/activate
celery -A attendance_system beat --loglevel=info
```

### 10. Run Django Development Server

```bash
python manage.py runserver
```

## Usage

### Employee Clock In/Out
1. Navigate to `http://localhost:8000/`
2. Enter your PIN using the numeric keypad
3. Click "Clock In/Out"
4. View confirmation screen with your details

### Admin Dashboard
1. Navigate to `http://localhost:8000/admin/dashboard/`
2. View real-time statistics and employee status
3. See today's hours for all employees

### Add New Employee
1. Go to `http://localhost:8000/admin/employees/add/`
2. Fill in:
   - Employee ID (auto-suggested, e.g., EMP001)
   - Employee Name
   - Email
   - PIN Code (4-6 digits, must be unique)
3. Click "Add Employee"

### Django Admin Panel
Access the Django admin at `http://localhost:8000/django-admin/`
- Manage all models
- View attendance taps
- Check email logs
- Configure system settings

## Project Structure

```
attend/
├── attendance/                 # Main app
│   ├── models.py              # Database models
│   ├── views.py               # View functions
│   ├── tasks.py               # Celery background tasks
│   ├── admin.py               # Admin panel configuration
│   ├── urls.py                # App URLs
│   └── templates/
│       └── attendance/
│           ├── welcome.html           # Employee PIN entry screen
│           ├── admin_dashboard.html   # Admin dashboard
│           └── add_employee.html      # Add employee form
├── attendance_system/          # Project settings
│   ├── settings.py            # Django settings
│   ├── celery.py              # Celery configuration
│   └── urls.py                # Main URL routing
├── manage.py
└── README.md
```

## Models

### EmployeeRegistry
Stores employee information and PIN codes.

### AttendanceTap
Records every clock in/out action with timestamp.

### DailySummary
Daily attendance summary with hours calculation per employee.

### TimesheetEdit
Audit log for admin changes to timesheets.

### EmailLog
Tracks all email notifications sent by the system.

### SystemSettings
Configurable system settings (key-value pairs).

## Celery Tasks Schedule

| Task | Schedule | Description |
|------|----------|-------------|
| auto_clock_out_check | Every 10 minutes | Auto clock-out after 8 hours or at 5 PM |
| send_missed_clock_out_reminders | Daily at 8 PM | Remind employees who forgot to clock out |
| send_weekly_reports | Friday at 5 PM | Send weekly attendance reports |

## API Endpoints

- `GET /` - Employee welcome screen
- `POST /clock/` - Process clock in/out action
- `GET /admin/dashboard/` - Admin dashboard
- `GET /admin/employees/add/` - Add employee form
- `POST /admin/employees/add/` - Submit new employee

## Business Logic

### Clock In/Out Detection
```python
tap_count = daily_summary.tap_count
action = 'IN' if tap_count % 2 == 0 else 'OUT'
```

### Break Deduction
```python
if raw_hours > 5:
    break_deduction = 0.5  # 30 minutes
else:
    break_deduction = 0
```

### Auto Clock-Out Triggers
1. After 8 hours from first clock in
2. At 5 PM (17:00)

## Timezone

All times are in **Australia/Sydney** timezone.

## Development Notes

- Emails print to console in development mode
- Change `EMAIL_BACKEND` in settings.py for production
- Auto-refresh enabled on admin dashboard (every 30 seconds)
- PIN entry supports keyboard input (0-9, Enter, Backspace, Escape)

## Security Features

- PIN displayed as dots (••••••)
- Employee PIN uniqueness validation
- CSRF protection on all forms
- Auto clock-out prevents time theft

## Troubleshooting

### Redis Connection Error
Make sure Redis is running:
```bash
redis-cli ping
# Should return: PONG
```

### Celery Not Running Tasks
Check if beat scheduler is running:
```bash
celery -A attendance_system beat --loglevel=info
```

### Database Connection Error
Verify MySQL credentials in settings.py and ensure database exists.

## License

This project is created for internal use.
