# Database Sync Guide: Railway <-> Local

## Prerequisites
- MySQL client installed locally (`mysql`, `mysqldump`)
- Access to Railway dashboard for DB credentials

---

## Step 1: Get Railway Database Credentials

Go to Railway Dashboard → Your Project → MySQL Service → Variables tab

You'll need:
```
MYSQLHOST=xxx.railway.internal (or public host)
MYSQLPORT=3306
MYSQLUSER=root
MYSQLPASSWORD=xxxxx
MYSQLDATABASE=railway
```

For external access, use the **Public Networking** host (not the internal one).

---

## Step 2: Export Production Data from Railway

```bash
# Replace with your Railway credentials
RAILWAY_HOST="your-railway-host.proxy.rlwy.net"
RAILWAY_PORT="your-port"
RAILWAY_USER="root"
RAILWAY_PASS="your-password"
RAILWAY_DB="railway"

# Export the database
mysqldump -h $RAILWAY_HOST -P $RAILWAY_PORT -u $RAILWAY_USER -p$RAILWAY_PASS $RAILWAY_DB > railway_backup.sql
```

---

## Step 3: Import to Local Database

```bash
# First, backup your local database
mysqldump -u root -p attendance_db > local_backup.sql

# Create a fresh database or use existing
mysql -u root -p -e "DROP DATABASE IF EXISTS attendance_db; CREATE DATABASE attendance_db;"

# Import Railway data
mysql -u root -p attendance_db < railway_backup.sql
```

---

## Step 4: Run V2 Migrations Locally

```bash
cd /home/vboxuser/Documents/attend
source env/bin/activate

# Run all migrations (this adds V2 tables)
python manage.py migrate

# Create V2 structures (departments, shifts)
python manage.py shell << 'EOF'
from attendance.models import Department, Shift

# Create departments if they don't exist
departments = [
    ('OFFS', 'Offshore', 'Offshore team'),
    ('IT', 'IT', 'IT department'),
    ('ADM', 'Admin', 'Administration'),
    ('WARE', 'Warehouse', 'Warehouse operations'),
]
for code, name, desc in departments:
    Department.objects.get_or_create(code=code, defaults={'name': name, 'description': desc})

# Create shifts if they don't exist
shifts = [
    ('MORN', 'Morning Shift', '07:00', '15:00'),
    ('DAY', 'Day Shift', '09:00', '17:00'),
    ('EVE', 'Evening Shift', '14:00', '22:00'),
    ('NIGHT', 'Night Shift', '22:00', '06:00'),
]
for code, name, start, end in shifts:
    Shift.objects.get_or_create(code=code, defaults={
        'name': name, 'start_time': start, 'end_time': end,
        'scheduled_hours': 8, 'break_duration_hours': 0.5,
        'early_arrival_grace_minutes': 15, 'late_departure_grace_minutes': 15
    })

print("Departments:", Department.objects.count())
print("Shifts:", Shift.objects.count())
EOF
```

---

## Step 5: Migrate V1 Employees to V2 (Optional)

If you have existing EmployeeRegistry records, migrate them to EmployeeProfile:

```bash
python manage.py migrate_v1_to_v2
```

Or manually in the shell:
```bash
python manage.py shell << 'EOF'
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from attendance.models import EmployeeRegistry, EmployeeProfile, Department

# Get default department
default_dept = Department.objects.first()

for emp in EmployeeRegistry.objects.filter(is_active=True):
    # Check if already migrated
    if EmployeeProfile.objects.filter(employee_id=emp.employee_id).exists():
        print(f"Skipping {emp.employee_id} - already exists")
        continue

    # Create Django User
    username = emp.employee_id.lower().replace(' ', '_')
    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            'email': emp.email,
            'first_name': emp.employee_name.split()[0] if emp.employee_name else '',
        }
    )
    if created:
        user.set_password('changeme123')  # Default password
        user.save()

    # Create EmployeeProfile
    profile, created = EmployeeProfile.objects.get_or_create(
        employee_id=emp.employee_id,
        defaults={
            'user': user,
            'employee_name': emp.employee_name,
            'email': emp.email,
            'department': default_dept,
            'role': 'EMPLOYEE',
            'pin_hash': make_password(emp.pin_code if emp.pin_code else '1234'),
            'nfc_id': emp.nfc_id,
        }
    )
    if created:
        print(f"Migrated: {emp.employee_id} -> {profile}")
    else:
        print(f"Exists: {emp.employee_id}")

print(f"\nTotal EmployeeProfiles: {EmployeeProfile.objects.count()}")
EOF
```

---

## Step 6: Create Test Accounts

```bash
python manage.py shell << 'EOF'
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from attendance.models import Department, Shift, EmployeeProfile

it_dept = Department.objects.get(code='IT')
admin_dept = Department.objects.get(code='ADM')
morning_shift = Shift.objects.get(code='MORN')

# Admin superuser
admin_user, _ = User.objects.get_or_create(username='admin', defaults={'email': 'admin@company.com', 'is_staff': True, 'is_superuser': True})
admin_user.set_password('admin123')
admin_user.is_staff = True
admin_user.is_superuser = True
admin_user.save()

# HR Admin
hr_user, _ = User.objects.get_or_create(username='hr_admin', defaults={'email': 'hr@company.com'})
hr_user.set_password('hr123')
hr_user.save()
EmployeeProfile.objects.get_or_create(user=hr_user, defaults={
    'employee_id': 'HR001', 'employee_name': 'HR Administrator', 'email': 'hr@company.com',
    'department': admin_dept, 'role': 'HR_ADMIN', 'default_shift': morning_shift,
    'pin_hash': make_password('1234')
})

# IT Manager
mgr_user, _ = User.objects.get_or_create(username='it_manager', defaults={'email': 'manager@company.com'})
mgr_user.set_password('manager123')
mgr_user.save()
mgr_profile, _ = EmployeeProfile.objects.get_or_create(user=mgr_user, defaults={
    'employee_id': 'MGR001', 'employee_name': 'IT Manager', 'email': 'manager@company.com',
    'department': it_dept, 'role': 'MANAGER', 'default_shift': morning_shift,
    'pin_hash': make_password('1234')
})
it_dept.manager = mgr_profile
it_dept.save()

print("Test accounts created!")
print("Admin: admin / admin123")
print("HR Admin: hr_admin / hr123")
print("IT Manager: it_manager / manager123")
EOF
```

---

## Step 7: Export Local Database

```bash
# Export the updated database
mysqldump -u root -p attendance_db > updated_db.sql
```

---

## Step 8: Push to Railway

```bash
# Import to Railway
mysql -h $RAILWAY_HOST -P $RAILWAY_PORT -u $RAILWAY_USER -p$RAILWAY_PASS $RAILWAY_DB < updated_db.sql
```

---

## Quick Commands Reference

```bash
# Export from Railway
mysqldump -h HOST -P PORT -u USER -pPASS DATABASE > backup.sql

# Import to local
mysql -u root -p attendance_db < backup.sql

# Export from local
mysqldump -u root -p attendance_db > export.sql

# Import to Railway
mysql -h HOST -P PORT -u USER -pPASS DATABASE < export.sql
```

---

## Troubleshooting

### Can't connect to Railway externally?
1. Go to Railway MySQL service
2. Settings → Public Networking → Enable
3. Use the public host/port provided

### SSL errors?
Add `--ssl-mode=REQUIRED` or `--ssl=0` to mysql commands

### Timeout errors?
Add `--connect-timeout=30` to mysql commands
