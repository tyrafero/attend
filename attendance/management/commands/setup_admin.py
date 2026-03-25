"""
Setup HR Admin profile for an existing superuser.

Usage:
    python manage.py setup_admin <username> <employee_id> <employee_name>
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from attendance.models import EmployeeProfile, Department


class Command(BaseCommand):
    help = 'Create HR Admin EmployeeProfile for an existing superuser'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Existing superuser username')
        parser.add_argument('employee_id', type=str, help='Employee ID (e.g., EMP001)')
        parser.add_argument('employee_name', type=str, help='Full name')
        parser.add_argument('--pin', type=str, default='1234', help='PIN for kiosk (default: 1234)')

    def handle(self, *args, **options):
        username = options['username']
        employee_id = options['employee_id']
        employee_name = options['employee_name']
        pin = options['pin']

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User "{username}" not found'))
            return

        if hasattr(user, 'employee_profile'):
            self.stdout.write(self.style.WARNING(f'User already has profile'))
            return

        dept, _ = Department.objects.get_or_create(
            code='ADM',
            defaults={'name': 'Admin', 'description': 'Administration'}
        )

        profile = EmployeeProfile.objects.create(
            user=user,
            employee_id=employee_id,
            employee_name=employee_name,
            email=user.email or f'{username}@example.com',
            pin_hash=make_password(pin),
            department=dept,
            role='HR_ADMIN',
            nfc_id=employee_id,
        )

        self.stdout.write(self.style.SUCCESS(f'\nAdmin profile created!'))
        self.stdout.write(f'  Employee ID: {employee_id}')
        self.stdout.write(f'  NFC tap URL: /?employee_id={employee_id}')
        self.stdout.write(f'  PIN: {pin}')
        self.stdout.write(f'  Role: HR_ADMIN')
