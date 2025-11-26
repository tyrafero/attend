from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, date
from decimal import Decimal
import pytz
from attendance.models import DailySummary, AttendanceTap, SystemSettings


class Command(BaseCommand):
    help = 'Manually clock out employees who were not auto-clocked out on a specific date'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Date in YYYY-MM-DD format (default: yesterday)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )

    def handle(self, *args, **options):
        sydney_tz = pytz.timezone('Australia/Sydney')

        # Parse date
        if options['date']:
            target_date = datetime.strptime(options['date'], '%Y-%m-%d').date()
        else:
            # Default to yesterday
            target_date = (timezone.now().astimezone(sydney_tz) - timezone.timedelta(days=1)).date()

        dry_run = options['dry_run']

        self.stdout.write(self.style.SUCCESS(f'=== Manual Clock-Out for {target_date} ==='))
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        self.stdout.write('')

        # Get system settings
        system_settings = SystemSettings.load()

        # Find all employees still clocked IN for that date
        employees_in = DailySummary.objects.filter(
            date=target_date,
            current_status='IN'
        )

        if employees_in.count() == 0:
            self.stdout.write(self.style.SUCCESS(f'No employees found with IN status on {target_date}'))
            return

        self.stdout.write(f'Found {employees_in.count()} employees to clock out:')
        self.stdout.write('')

        clocked_out_count = 0

        for summary in employees_in:
            self.stdout.write(f'Processing: {summary.employee_name} (ID: {summary.employee_id})')
            self.stdout.write(f'  First IN: {summary.first_clock_in}')

            if not summary.first_clock_in:
                self.stdout.write(self.style.ERROR('  ERROR: No first_clock_in time - skipping'))
                continue

            # Use office end time as clock-out time
            clock_out_time = system_settings.office_end_time

            if not dry_run:
                # Create auto clock-out tap
                AttendanceTap.objects.create(
                    employee_id=summary.employee_id,
                    employee_name=summary.employee_name,
                    action='OUT',
                    notes='Manual clock-out (admin correction)'
                )

                # Update daily summary
                summary.last_clock_out = clock_out_time
                summary.tap_count += 1
                summary.current_status = 'OUT'

                # Calculate hours
                first_in_dt = datetime.combine(target_date, summary.first_clock_in)
                last_out_dt = datetime.combine(target_date, clock_out_time)
                time_diff = last_out_dt - first_in_dt
                raw_hours = Decimal(time_diff.total_seconds() / 3600)
                summary.raw_hours = raw_hours

                # Apply break deduction
                if raw_hours > 5:
                    summary.break_deduction = system_settings.break_duration_hours
                else:
                    summary.break_deduction = Decimal('0')

                summary.final_hours = summary.raw_hours - summary.break_deduction
                summary.save()

                self.stdout.write(self.style.SUCCESS(f'  ✓ Clocked out at {clock_out_time}'))
                self.stdout.write(f'  Raw hours: {summary.raw_hours}h')
                self.stdout.write(f'  Break deduction: {summary.break_deduction}h')
                self.stdout.write(f'  Final hours: {summary.final_hours}h')
                clocked_out_count += 1
            else:
                # Dry run - just show what would happen
                first_in_dt = datetime.combine(target_date, summary.first_clock_in)
                last_out_dt = datetime.combine(target_date, clock_out_time)
                time_diff = last_out_dt - first_in_dt
                raw_hours = Decimal(time_diff.total_seconds() / 3600)

                if raw_hours > 5:
                    break_deduction = system_settings.break_duration_hours
                else:
                    break_deduction = Decimal('0')

                final_hours = raw_hours - break_deduction

                self.stdout.write(f'  Would clock out at {clock_out_time}')
                self.stdout.write(f'  Raw hours: {raw_hours}h')
                self.stdout.write(f'  Break deduction: {break_deduction}h')
                self.stdout.write(f'  Final hours: {final_hours}h')

            self.stdout.write('')

        if not dry_run:
            self.stdout.write(self.style.SUCCESS(f'✓ Successfully clocked out {clocked_out_count} employees'))
        else:
            self.stdout.write(self.style.WARNING(f'DRY RUN: Would clock out {employees_in.count()} employees'))
            self.stdout.write('Run without --dry-run to apply changes')
