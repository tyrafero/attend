"""
Management command to migrate v1 EmployeeRegistry data to v2 EmployeeProfile
This creates User accounts, hashes PINs, and links to departments

Usage: python manage.py migrate_v1_to_v2
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.db import transaction
from attendance.models import (
    EmployeeRegistry, EmployeeProfile, Department, TILBalance
)


class Command(BaseCommand):
    help = 'Migrate v1 EmployeeRegistry to v2 EmployeeProfile with User accounts'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be migrated without actually migrating',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write(self.style.WARNING('V1 to V2 Employee Migration'))
        self.stdout.write(self.style.WARNING('=' * 70))

        if dry_run:
            self.stdout.write(self.style.NOTICE('DRY RUN MODE - No changes will be made'))

        # Step 1: Ensure departments exist
        self.stdout.write('\nStep 1: Checking departments...')
        departments_data = [
            {'code': 'IT', 'name': 'IT'},
            {'code': 'OFFS', 'name': 'Offshore'},
            {'code': 'ADM', 'name': 'Admin'},
            {'code': 'WARE', 'name': 'Warehouse'},
        ]

        default_dept = None
        for dept_data in departments_data:
            if not dry_run:
                dept, created = Department.objects.get_or_create(
                    code=dept_data['code'],
                    defaults={'name': dept_data['name'], 'is_active': True}
                )
                if created:
                    self.stdout.write(
                        self.style.SUCCESS(f'  ✓ Created department: {dept.name}')
                    )
                else:
                    self.stdout.write(f'  - Department exists: {dept.name}')

                if dept.code == 'IT':
                    default_dept = dept
            else:
                self.stdout.write(f'  [DRY RUN] Would create/check department: {dept_data["name"]}')

        if not dry_run:
            default_dept = Department.objects.get(code='IT')

        # Step 2: Migrate employees
        self.stdout.write('\nStep 2: Migrating employees...')
        v1_employees = EmployeeRegistry.objects.all()
        total = v1_employees.count()
        migrated = 0
        skipped = 0
        errors = 0

        self.stdout.write(f'Found {total} employees in v1 registry\n')

        for emp in v1_employees:
            try:
                # Check if already migrated
                if EmployeeProfile.objects.filter(employee_id=emp.employee_id).exists():
                    self.stdout.write(
                        self.style.NOTICE(f'  ⊘ Skipped (already migrated): {emp.employee_name}')
                    )
                    skipped += 1
                    continue

                if dry_run:
                    self.stdout.write(
                        f'  [DRY RUN] Would migrate: {emp.employee_name} ({emp.employee_id})'
                    )
                    migrated += 1
                    continue

                # Start transaction for this employee
                with transaction.atomic():
                    # Create Django User
                    username = emp.employee_id
                    email = emp.email

                    user, user_created = User.objects.get_or_create(
                        username=username,
                        defaults={
                            'email': email,
                            'first_name': emp.employee_name.split()[0] if emp.employee_name else '',
                            'last_name': ' '.join(emp.employee_name.split()[1:]) if len(emp.employee_name.split()) > 1 else '',
                        }
                    )

                    # Set temporary password if user was just created
                    if user_created:
                        user.set_password(f'temp_{emp.employee_id}')
                        user.save()

                    # Hash the PIN (v1 had plaintext PINs - SECURITY FIX!)
                    pin_to_hash = emp.pin_code if emp.pin_code else '1234'
                    pin_hash = make_password(pin_to_hash)

                    # Create EmployeeProfile
                    profile = EmployeeProfile.objects.create(
                        user=user,
                        employee_id=emp.employee_id,
                        employee_name=emp.employee_name,
                        email=emp.email,
                        pin_hash=pin_hash,
                        nfc_id=emp.nfc_id,
                        department=default_dept,  # Default to IT department
                        role='EMPLOYEE',  # Default role
                        is_active=emp.is_active
                    )

                    # Create TIL balance
                    TILBalance.objects.create(employee=profile)

                    self.stdout.write(
                        self.style.SUCCESS(f'  ✓ Migrated: {emp.employee_name} ({emp.employee_id})')
                    )
                    migrated += 1

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  ✗ Error migrating {emp.employee_name}: {str(e)}')
                )
                errors += 1

        # Summary
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.WARNING('MIGRATION SUMMARY'))
        self.stdout.write('=' * 70)
        self.stdout.write(f'Total employees:     {total}')
        self.stdout.write(self.style.SUCCESS(f'Migrated:            {migrated}'))
        self.stdout.write(self.style.NOTICE(f'Skipped (existing):  {skipped}'))
        if errors > 0:
            self.stdout.write(self.style.ERROR(f'Errors:              {errors}'))
        self.stdout.write('=' * 70)

        if dry_run:
            self.stdout.write(self.style.NOTICE('\nDRY RUN COMPLETE - No changes were made'))
            self.stdout.write('Run without --dry-run to perform actual migration')
        else:
            self.stdout.write(self.style.SUCCESS('\n✓ MIGRATION COMPLETE'))
            self.stdout.write('\nNext steps:')
            self.stdout.write('1. Assign employees to departments via Django admin')
            self.stdout.write('2. Assign managers to employees')
            self.stdout.write('3. Create shift templates')
            self.stdout.write('4. Notify employees of their temporary passwords: temp_<employee_id>')
