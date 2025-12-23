#!/bin/bash

echo "=== Auto Clock-Out Monitoring Dashboard ==="
echo ""

cd /home/vboxuser/Documents/attend
source env/bin/activate

python manage.py shell << 'PYTHON'
from attendance.models import DailySummary, AttendanceTap, SystemSettings
from django.utils import timezone
import pytz

sydney_tz = pytz.timezone('Australia/Sydney')
now = timezone.now().astimezone(sydney_tz)
today = now.date()

settings = SystemSettings.load()

print(f"🕐 Current Time: {now.strftime('%I:%M %p')}")
print(f"🏢 Office End Time: {settings.office_end_time.strftime('%I:%M %p')}")
print(f"⏱️  Required Shift: {settings.required_shift_hours} hours")
print(f"✅ Auto Clock-Out: {'Enabled' if settings.enable_auto_clockout else 'Disabled'}")
print()

# Employees currently IN
employees_in = DailySummary.objects.filter(date=today, current_status='IN')
print(f"👥 Employees Currently IN: {employees_in.count()}")

if employees_in.exists():
    print()
    for emp in employees_in:
        if emp.first_clock_in:
            hours_elapsed = (now - sydney_tz.localize(
                timezone.datetime.combine(today, emp.first_clock_in)
            )).total_seconds() / 3600
            
            will_auto_out = (
                now.time() >= settings.office_end_time or 
                hours_elapsed >= float(settings.required_shift_hours)
            )
            
            status = "🔴 Will auto clock-out" if will_auto_out else "🟢 Still working"
            
            print(f"  {emp.employee_name}:")
            print(f"    Clock In: {emp.first_clock_in.strftime('%I:%M %p')}")
            print(f"    Hours Elapsed: {hours_elapsed:.1f}h")
            print(f"    Status: {status}")
            print()

# Recent auto clock-outs today
auto_clockouts = AttendanceTap.objects.filter(
    timestamp__date=today,
    action='OUT',
    notes='Auto clock-out'
).order_by('-timestamp')

if auto_clockouts.exists():
    print(f"🤖 Auto Clock-Outs Today: {auto_clockouts.count()}")
    for tap in auto_clockouts[:5]:
        print(f"  - {tap.employee_name} at {tap.timestamp.astimezone(sydney_tz).strftime('%I:%M %p')}")
else:
    print("🤖 No auto clock-outs today yet")
PYTHON
