from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime
import pytz
from attendance.models import DailySummary, SystemSettings, AttendanceTap
from attendance.tasks import auto_clock_out_check


class Command(BaseCommand):
    help = 'Debug auto clock-out functionality'

    def handle(self, *args, **options):
        sydney_tz = pytz.timezone('Australia/Sydney')
        now = timezone.now().astimezone(sydney_tz)
        today = now.date()

        self.stdout.write(self.style.SUCCESS('=== AUTO CLOCK-OUT DEBUG ==='))
        self.stdout.write(f'Current Sydney time: {now}')
        self.stdout.write(f'Current time: {now.time()}')
        self.stdout.write(f'Current date: {today}')
        self.stdout.write('')

        # Check system settings
        system_settings = SystemSettings.load()
        self.stdout.write(self.style.WARNING('System Settings:'))
        self.stdout.write(f'  Auto clockout enabled: {system_settings.enable_auto_clockout}')
        self.stdout.write(f'  Office end time: {system_settings.office_end_time}')
        self.stdout.write(f'  Required shift hours: {system_settings.required_shift_hours}')
        self.stdout.write('')

        # Check employees currently IN
        employees_in = DailySummary.objects.filter(date=today, current_status='IN')
        self.stdout.write(self.style.WARNING(f'Employees currently IN: {employees_in.count()}'))

        for emp in employees_in:
            if emp.first_clock_in:
                first_in_dt = datetime.combine(today, emp.first_clock_in)
                hours_elapsed = (now - sydney_tz.localize(first_in_dt)).total_seconds() / 3600

                should_clock_out = False
                reason = ""

                if now.time() >= system_settings.office_end_time:
                    should_clock_out = True
                    reason = f"Office end time reached ({system_settings.office_end_time})"
                elif hours_elapsed >= float(system_settings.required_shift_hours):
                    should_clock_out = True
                    reason = f"Required shift hours reached ({hours_elapsed:.2f}h >= {system_settings.required_shift_hours}h)"
                else:
                    reason = f"Not ready (Hours: {hours_elapsed:.2f}/{system_settings.required_shift_hours}, Time: {now.time()} < {system_settings.office_end_time})"

                status_icon = "✓ SHOULD CLOCK OUT" if should_clock_out else "✗ NOT YET"
                self.stdout.write(f'  [{status_icon}] {emp.employee_name} (ID: {emp.employee_id})')
                self.stdout.write(f'      First IN: {emp.first_clock_in}')
                self.stdout.write(f'      Hours elapsed: {hours_elapsed:.2f}')
                self.stdout.write(f'      Reason: {reason}')
            else:
                self.stdout.write(f'  [ERROR] {emp.employee_name}: No first_clock_in time!')

        self.stdout.write('')

        # Check recent attendance taps
        recent_taps = AttendanceTap.objects.filter(timestamp__date=today).order_by('-timestamp')[:10]
        self.stdout.write(self.style.WARNING(f'Recent taps today: {recent_taps.count()}'))
        for tap in recent_taps:
            tap_time = tap.timestamp.astimezone(sydney_tz)
            self.stdout.write(f'  {tap.employee_name}: {tap.action} at {tap_time.time()} (Notes: {tap.notes or "None"})')

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=== RUNNING AUTO CLOCK-OUT TASK ==='))
        result = auto_clock_out_check()
        self.stdout.write(f'Task result: {result}')
        self.stdout.write('')

        # Check again after running
        employees_in_after = DailySummary.objects.filter(date=today, current_status='IN')
        self.stdout.write(self.style.SUCCESS(f'Employees still IN after task: {employees_in_after.count()}'))
