"""
Management command to backfill nfc_id for existing employees who don't have one set.
This ensures all employees can use NFC tap functionality.

Usage:
    python manage.py backfill_nfc_ids
    python manage.py backfill_nfc_ids --dry-run  # Preview changes without saving
"""
from django.core.management.base import BaseCommand
from attendance.models import EmployeeProfile, EmployeeRegistry


class Command(BaseCommand):
    help = 'Backfill nfc_id with employee_id for employees who have empty nfc_id'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without saving',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes will be saved\n'))

        # Backfill V2 EmployeeProfile
        self.stdout.write('Checking V2 EmployeeProfile records...')
        v2_profiles = EmployeeProfile.objects.filter(nfc_id__isnull=True) | EmployeeProfile.objects.filter(nfc_id='')
        v2_count = v2_profiles.count()

        if v2_count > 0:
            self.stdout.write(f'  Found {v2_count} profiles with empty nfc_id')
            for profile in v2_profiles:
                self.stdout.write(f'    - {profile.employee_id}: {profile.employee_name}')
                if not dry_run:
                    profile.nfc_id = profile.employee_id
                    profile.save(update_fields=['nfc_id'])

            if not dry_run:
                self.stdout.write(self.style.SUCCESS(f'  Updated {v2_count} V2 profiles'))
        else:
            self.stdout.write(self.style.SUCCESS('  All V2 profiles have nfc_id set'))

        # Backfill V1 EmployeeRegistry (for backward compatibility)
        self.stdout.write('\nChecking V1 EmployeeRegistry records...')
        v1_employees = EmployeeRegistry.objects.filter(nfc_id__isnull=True) | EmployeeRegistry.objects.filter(nfc_id='')
        v1_count = v1_employees.count()

        if v1_count > 0:
            self.stdout.write(f'  Found {v1_count} employees with empty nfc_id')
            for emp in v1_employees:
                self.stdout.write(f'    - {emp.employee_id}: {emp.employee_name}')
                if not dry_run:
                    emp.nfc_id = emp.employee_id
                    emp.save(update_fields=['nfc_id'])

            if not dry_run:
                self.stdout.write(self.style.SUCCESS(f'  Updated {v1_count} V1 employees'))
        else:
            self.stdout.write(self.style.SUCCESS('  All V1 employees have nfc_id set'))

        # Summary
        self.stdout.write('\n' + '=' * 50)
        total = v2_count + v1_count
        if dry_run:
            self.stdout.write(self.style.WARNING(f'Would update {total} records (use without --dry-run to apply)'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Successfully updated {total} records'))
