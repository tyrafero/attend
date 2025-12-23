from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, time, timedelta
from decimal import Decimal
import pytz
from attendance.models import DailySummary, AttendanceTap, SystemSettings


class Command(BaseCommand):
    help = 'Populate database with sample attendance data for testing'

    def handle(self, *args, **options):
        sydney_tz = pytz.timezone('Australia/Sydney')
        today = timezone.now().astimezone(sydney_tz).date()

        # Calculate this week's Monday to Friday
        days_since_monday = today.weekday()
        monday = today - timedelta(days=days_since_monday)

        # Get system settings
        system_settings = SystemSettings.load()

        self.stdout.write(self.style.SUCCESS('=== Populating Test Attendance Data ==='))
        self.stdout.write(f'Week: {monday} to {monday + timedelta(days=4)}')
        self.stdout.write('')

        # Define employees with their patterns
        employees = [
            {
                'id': '101',
                'name': 'Ashutosh Singh Khadka',
                'pattern': 'early_bird',  # Arrives early, works long hours
            },
            {
                'id': '103',
                'name': 'Kam Leung',
                'pattern': 'overtime',  # Works most hours
            },
            {
                'id': 'TEST001',
                'name': 'Test Employee (Auto Clock-Out)',
                'pattern': 'normal',  # Regular hours
            },
        ]

        # Clear existing data for this week
        DailySummary.objects.filter(
            date__gte=monday,
            date__lte=monday + timedelta(days=4)
        ).delete()

        # Create attendance records
        for day_offset in range(5):  # Monday to Friday
            current_date = monday + timedelta(days=day_offset)

            for emp in employees:
                # Determine clock-in and hours based on pattern
                if emp['pattern'] == 'early_bird':
                    # Arrives earliest (6:30-7:00 AM), works 8-9 hours
                    clock_in_hour = 6
                    clock_in_minute = 30 + (day_offset * 5)  # Slight variation
                    work_hours = 8.5 + (day_offset * 0.2)
                elif emp['pattern'] == 'overtime':
                    # Arrives normal time but works longest hours
                    clock_in_hour = 7
                    clock_in_minute = 45 + (day_offset * 3)
                    work_hours = 9.5 + (day_offset * 0.3)  # Most hours
                else:  # normal
                    # Regular hours
                    clock_in_hour = 8
                    clock_in_minute = 0 + (day_offset * 2)
                    work_hours = 8.0

                first_clock_in = time(clock_in_hour, clock_in_minute, 0)

                # Calculate clock out time
                clock_in_dt = datetime.combine(current_date, first_clock_in)
                clock_out_dt = clock_in_dt + timedelta(hours=work_hours)
                last_clock_out = clock_out_dt.time()

                # Calculate hours
                raw_hours = Decimal(str(work_hours))
                break_deduction = system_settings.break_duration_hours if raw_hours > 5 else Decimal('0')
                final_hours = raw_hours - break_deduction

                # Create daily summary
                DailySummary.objects.create(
                    date=current_date,
                    employee_id=emp['id'],
                    employee_name=emp['name'],
                    first_clock_in=first_clock_in,
                    last_clock_out=last_clock_out,
                    raw_hours=raw_hours,
                    break_deduction=break_deduction,
                    final_hours=final_hours,
                    current_status='OUT',
                    tap_count=2
                )

                self.stdout.write(
                    f"  {emp['name'][:20]:20} | {current_date} | "
                    f"IN: {first_clock_in.strftime('%H:%M')} | "
                    f"OUT: {last_clock_out.strftime('%H:%M')} | "
                    f"Hours: {final_hours}h"
                )

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('✓ Test data populated successfully!'))
        self.stdout.write('')
        self.stdout.write('Summary:')
        self.stdout.write('  - Ashutosh: Early Bird (arrives 6:30-7:00 AM)')
        self.stdout.write('  - Kam Leung: Overtime Champion (works most hours)')
        self.stdout.write('  - Test Employee: Regular hours')
