from django.db import models
from django.contrib.auth.models import User


class EmployeeRegistry(models.Model):
    employee_id = models.CharField(max_length=50, unique=True)  # EMP123
    employee_name = models.CharField(max_length=200)
    email = models.EmailField()
    pin_code = models.CharField(max_length=6, blank=True)  # 4-6 digit PIN (optional if using NFC)
    nfc_id = models.CharField(max_length=100, blank=True, unique=True, null=True)  # NFC card unique ID
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Employee'
        verbose_name_plural = 'Employees'
        ordering = ['employee_name']

    def save(self, *args, **kwargs):
        # Auto-sync nfc_id with employee_id if nfc_id is empty
        if not self.nfc_id:
            self.nfc_id = self.employee_id
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee_id} - {self.employee_name}"


class AttendanceTap(models.Model):
    ACTION_CHOICES = [
        ('IN', 'Clock In'),
        ('OUT', 'Clock Out'),
    ]

    timestamp = models.DateTimeField(auto_now_add=True)
    employee_id = models.CharField(max_length=50)
    employee_name = models.CharField(max_length=200)
    action = models.CharField(max_length=3, choices=ACTION_CHOICES)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Attendance Tap'
        verbose_name_plural = 'Attendance Taps'
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.employee_name} - {self.action} at {self.timestamp}"


class DailySummary(models.Model):
    STATUS_CHOICES = [
        ('IN', 'Clocked In'),
        ('OUT', 'Clocked Out'),
    ]

    # ForeignKey for easy dropdown selection in admin
    selected_employee = models.ForeignKey(
        EmployeeRegistry,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='daily_summaries',
        help_text='Select employee from dropdown',
        verbose_name='Employee'
    )

    # Keep these fields for backward compatibility and denormalized access
    date = models.DateField()
    employee_id = models.CharField(max_length=50)
    employee_name = models.CharField(max_length=200)
    first_clock_in = models.TimeField(null=True, blank=True)
    last_clock_out = models.TimeField(null=True, blank=True)
    raw_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    break_deduction = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    final_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    current_status = models.CharField(max_length=3, choices=STATUS_CHOICES, default='OUT')
    tap_count = models.IntegerField(default=0)

    class Meta:
        verbose_name = 'Daily Summary'
        verbose_name_plural = 'Daily Summaries'
        unique_together = ['date', 'employee_id']
        ordering = ['-date', 'employee_name']

    def save(self, *args, **kwargs):
        # Auto-populate employee_id and employee_name from ForeignKey if set
        if self.selected_employee:
            self.employee_id = self.selected_employee.employee_id
            self.employee_name = self.selected_employee.employee_name

        # Auto-calculate hours if both clock-in and clock-out times are set
        if self.first_clock_in and self.last_clock_out:
            from datetime import datetime
            from decimal import Decimal

            # Calculate raw hours
            first_in_dt = datetime.combine(self.date, self.first_clock_in)
            last_out_dt = datetime.combine(self.date, self.last_clock_out)
            time_diff = last_out_dt - first_in_dt
            self.raw_hours = Decimal(time_diff.total_seconds() / 3600)

            # Apply break deduction from system settings
            system_settings = SystemSettings.load()
            if self.raw_hours > 5:
                self.break_deduction = system_settings.break_duration_hours
            else:
                self.break_deduction = Decimal('0')

            # Calculate final hours
            self.final_hours = self.raw_hours - self.break_deduction

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee_name} - {self.date} ({self.final_hours}h)"


class TimesheetEdit(models.Model):
    edited_at = models.DateTimeField(auto_now_add=True)
    edited_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    employee_id = models.CharField(max_length=50)
    employee_name = models.CharField(max_length=200)
    date = models.DateField()
    field_changed = models.CharField(max_length=100)  # e.g., "first_clock_in", "final_hours"
    old_value = models.CharField(max_length=200)
    new_value = models.CharField(max_length=200)
    reason = models.TextField()

    class Meta:
        verbose_name = 'Timesheet Edit'
        verbose_name_plural = 'Timesheet Edits'
        ordering = ['-edited_at']

    def __str__(self):
        return f"{self.employee_name} - {self.field_changed} edited on {self.date}"


class LeaveRecord(models.Model):
    LEAVE_TYPE_CHOICES = [
        ('ANNUAL', 'Annual Leave'),
        ('SICK', 'Sick Leave'),
        ('UNPAID', 'Unpaid Leave'),
        ('TIL', 'Time in Lieu'),
    ]

    STATUS_CHOICES = [
        ('PENDING', 'Pending Approval'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('CANCELLED', 'Cancelled'),
    ]

    # Employee selection (follows DailySummary pattern) - V1 compatibility
    selected_employee = models.ForeignKey(
        EmployeeRegistry,
        on_delete=models.CASCADE,
        related_name='leave_records',
        null=True,
        blank=True,
        help_text='Select employee from dropdown (V1)'
    )

    # V2 Employee Profile link
    employee_profile = models.ForeignKey(
        'EmployeeProfile',
        on_delete=models.CASCADE,
        related_name='leave_records',
        null=True,
        blank=True,
        help_text='Employee profile (V2)'
    )

    # Denormalized fields (auto-populated)
    employee_id = models.CharField(max_length=50)
    employee_name = models.CharField(max_length=200)

    # Leave details
    leave_type = models.CharField(max_length=20, choices=LEAVE_TYPE_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True)

    # Status and approval workflow
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    approved_by = models.ForeignKey(
        'EmployeeProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_leaves',
        help_text='Manager who approved/rejected'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, help_text='Reason for rejection')
    manager_comments = models.TextField(blank=True, help_text='Manager comments')

    # Auto-calculated fields
    hours_per_day = models.DecimalField(max_digits=4, decimal_places=2, default=8.0)
    total_days = models.IntegerField(default=0)
    total_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    # Audit trail
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = 'Leave Record'
        verbose_name_plural = 'Leave Records'
        ordering = ['-start_date']

    def clean(self):
        """Validate dates"""
        from django.core.exceptions import ValidationError
        if self.end_date < self.start_date:
            raise ValidationError('End date cannot be before start date')

    def save(self, *args, **kwargs):
        """Auto-populate fields and calculate totals"""
        from datetime import timedelta
        from decimal import Decimal

        # Auto-populate employee fields from V2 EmployeeProfile
        if self.employee_profile:
            self.employee_id = self.employee_profile.employee_id
            self.employee_name = self.employee_profile.employee_name
        # Fallback to V1 selected_employee
        elif self.selected_employee:
            self.employee_id = self.selected_employee.employee_id
            self.employee_name = self.selected_employee.employee_name

        # Get hours per day from settings
        system_settings = SystemSettings.load()
        self.hours_per_day = system_settings.default_leave_hours_per_day

        # Calculate business days (Mon-Fri only)
        current_date = self.start_date
        business_days = 0
        while current_date <= self.end_date:
            if current_date.weekday() < 5:  # 0-4 = Monday-Friday
                business_days += 1
            current_date += timedelta(days=1)

        self.total_days = business_days
        self.total_hours = Decimal(str(business_days)) * self.hours_per_day

        super().save(*args, **kwargs)

    def get_dates_list(self):
        """Return list of business day dates in leave period"""
        from datetime import timedelta
        dates = []
        current_date = self.start_date
        while current_date <= self.end_date:
            if current_date.weekday() < 5:
                dates.append(current_date)
            current_date += timedelta(days=1)
        return dates

    def __str__(self):
        return f"{self.employee_name} - {self.get_leave_type_display()} ({self.start_date} to {self.end_date})"


class EmailLog(models.Model):
    STATUS_CHOICES = [
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('PENDING', 'Pending'),
    ]

    timestamp = models.DateTimeField(auto_now_add=True)
    email_type = models.CharField(max_length=50)
    recipient = models.EmailField()
    employee_id = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    details = models.TextField()

    class Meta:
        verbose_name = 'Email Log'
        verbose_name_plural = 'Email Logs'
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.email_type} to {self.recipient} - {self.status}"


class SystemSettings(models.Model):
    """Singleton model for system-wide attendance settings"""

    # Office Hours
    office_start_time = models.TimeField(default='07:00', help_text='Office opening time (e.g., 07:00)')
    office_end_time = models.TimeField(default='17:00', help_text='Office closing time (e.g., 17:00). No clock in/out after this time.')

    # Shift Configuration
    required_shift_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=8.0,
        help_text='Required shift duration including break (hours)'
    )
    break_duration_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0.5,
        help_text='Unpaid break duration (hours). Deducted from shifts > 5 hours'
    )

    # Auto Clock-Out Settings
    enable_auto_clockout = models.BooleanField(
        default=True,
        help_text='Automatically clock out employees at office closing time or after shift hours'
    )
    auto_clockout_interval = models.IntegerField(
        default=30,
        help_text='How often to check for auto clock-out (minutes)'
    )

    # Email Notifications
    enable_weekly_reports = models.BooleanField(
        default=True,
        help_text='Send weekly attendance reports to employees'
    )
    weekly_report_day = models.IntegerField(
        default=4,  # Friday (0=Monday, 4=Friday)
        help_text='Day of week to send reports (0=Monday, 4=Friday, 6=Sunday)'
    )
    weekly_report_time = models.TimeField(
        default='17:00',
        help_text='Time to send weekly reports'
    )

    enable_early_clockout_alerts = models.BooleanField(
        default=False,
        help_text='Send alerts when employees clock out before completing required shift hours'
    )

    # Leave Management
    default_leave_hours_per_day = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=8.0,
        help_text='Default hours per day for leave calculations'
    )
    enable_leave_notifications = models.BooleanField(
        default=True,
        help_text='Send email notifications when leaves are created'
    )

    class Meta:
        verbose_name = 'System Settings'
        verbose_name_plural = 'System Settings'

    def save(self, *args, **kwargs):
        # Ensure only one instance exists (singleton)
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Prevent deletion
        pass

    @classmethod
    def load(cls):
        """Load or create the singleton settings instance"""
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return 'System Settings'


class AttendanceReport(models.Model):
    """Proxy model for Reports section in admin - doesn't create a table"""
    class Meta:
        managed = False  # Don't create database table
        verbose_name = 'Attendance Report'
        verbose_name_plural = 'Attendance Reports'
        app_label = 'attendance'
        # This will make it appear in the admin under a "Reports" section


# ============================================================================
# V2 MODELS - New architecture with User authentication and department structure
# ============================================================================

class Department(models.Model):
    """Department model for organizing employees (Offshore, IT, Admin, Warehouse)"""
    DEPARTMENT_CODES = [
        ('OFFS', 'Offshore'),
        ('IT', 'IT'),
        ('ADM', 'Admin'),
        ('WARE', 'Warehouse'),
    ]

    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True, choices=DEPARTMENT_CODES)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Manager will be set after EmployeeProfile is created (nullable)
    manager = models.ForeignKey(
        'EmployeeProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_departments',
        help_text='Department manager'
    )

    class Meta:
        verbose_name = 'Department'
        verbose_name_plural = 'Departments'
        ordering = ['name']

    def __str__(self):
        return f"{self.code} - {self.name}"


class Shift(models.Model):
    """Shift templates (e.g., Morning Shift 7 AM - 3 PM)"""
    SHIFT_CODES = [
        ('MORN', 'Morning'),
        ('DAY', 'Day'),
        ('EVE', 'Evening'),
        ('NIGHT', 'Night'),
    ]

    name = models.CharField(max_length=100, help_text='e.g., Morning Shift, Day Shift')
    code = models.CharField(max_length=20, unique=True, choices=SHIFT_CODES)

    # Time windows
    start_time = models.TimeField(help_text='Shift start time (e.g., 07:00)')
    end_time = models.TimeField(help_text='Shift end time (e.g., 15:00)')

    # Duration config
    scheduled_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=8.0,
        help_text='Scheduled shift duration (hours)'
    )
    break_duration_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0.5,
        help_text='Break duration (hours)'
    )

    # Variance tolerances for Early Bird detection
    early_arrival_grace_minutes = models.IntegerField(
        default=15,
        help_text='Minutes early is considered normal (beyond this = Early Bird)'
    )
    late_departure_grace_minutes = models.IntegerField(
        default=15,
        help_text='Minutes late is considered normal'
    )

    # Optional department-specific shifts
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='shifts',
        null=True,
        blank=True,
        help_text='Department this shift belongs to (optional)'
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Shift'
        verbose_name_plural = 'Shifts'
        ordering = ['start_time']

    def __str__(self):
        return f"{self.name} ({self.start_time} - {self.end_time})"


class EmployeeProfile(models.Model):
    """Extended employee profile linked to Django User for authentication"""
    ROLE_CHOICES = [
        ('EMPLOYEE', 'Employee'),
        ('MANAGER', 'Manager'),
        ('HR_ADMIN', 'HR/Admin'),
    ]

    # Link to Django User (for username/password auth)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='employee_profile',
        help_text='Django user account for login'
    )

    # Employee details (from v1 EmployeeRegistry)
    employee_id = models.CharField(max_length=50, unique=True, help_text='Unique employee ID')
    employee_name = models.CharField(max_length=200)
    email = models.EmailField()

    # PIN authentication (HASHED for security)
    pin_hash = models.CharField(
        max_length=128,
        help_text='Hashed PIN for kiosk clock in/out'
    )
    pin_updated_at = models.DateTimeField(auto_now_add=True)

    # Department and role
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name='employees',
        help_text='Employee department'
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='EMPLOYEE',
        help_text='User role (Employee, Manager, HR/Admin)'
    )

    # Shift assignment
    default_shift = models.ForeignKey(
        Shift,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employees',
        help_text='Default shift for this employee'
    )

    # Manager assignment (for employees only)
    manager = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='team_members',
        help_text='Direct manager (for employees only)'
    )

    # NFC (keep backward compatibility from v1)
    nfc_id = models.CharField(
        max_length=100,
        blank=True,
        unique=True,
        null=True,
        help_text='NFC card ID (optional)'
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Employee Profile (V2)'
        verbose_name_plural = 'Employee Profiles (V2)'
        ordering = ['employee_name']

    def __str__(self):
        return f"{self.employee_id} - {self.employee_name} ({self.get_role_display()})"

    def is_manager_or_above(self):
        """Check if user is manager or HR"""
        return self.role in ['MANAGER', 'HR_ADMIN']

    def is_hr_admin(self):
        """Check if user is HR admin"""
        return self.role == 'HR_ADMIN'


class ShiftAssignment(models.Model):
    """Daily shift assignments for employees (allows custom shifts and pre-approvals)"""
    employee = models.ForeignKey(
        EmployeeProfile,
        on_delete=models.CASCADE,
        related_name='shift_assignments',
        help_text='Employee assigned to this shift'
    )
    shift = models.ForeignKey(
        Shift,
        on_delete=models.CASCADE,
        help_text='Shift template'
    )
    date = models.DateField(help_text='Date for this shift assignment')

    # Custom overrides (optional)
    custom_start_time = models.TimeField(
        null=True,
        blank=True,
        help_text='Custom start time (overrides shift template)'
    )
    custom_end_time = models.TimeField(
        null=True,
        blank=True,
        help_text='Custom end time (overrides shift template)'
    )

    # Pre-approved early/overtime (for TIL calculation)
    pre_approved_early_start = models.BooleanField(
        default=False,
        help_text='Manager pre-approved early start'
    )
    pre_approved_overtime = models.BooleanField(
        default=False,
        help_text='Manager pre-approved overtime'
    )
    approved_early_minutes = models.IntegerField(
        default=0,
        help_text='Pre-approved early start minutes'
    )
    approved_overtime_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0,
        help_text='Pre-approved overtime hours'
    )

    # Approval tracking
    approved_by = models.ForeignKey(
        EmployeeProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_shift_assignments',
        help_text='Manager who approved'
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Shift Assignment'
        verbose_name_plural = 'Shift Assignments'
        unique_together = ['employee', 'date']
        ordering = ['-date', 'employee__employee_name']

    def __str__(self):
        return f"{self.employee.employee_name} - {self.shift.name} on {self.date}"

    def get_effective_start_time(self):
        """Get actual start time (custom or shift template)"""
        return self.custom_start_time if self.custom_start_time else self.shift.start_time

    def get_effective_end_time(self):
        """Get actual end time (custom or shift template)"""
        return self.custom_end_time if self.custom_end_time else self.shift.end_time


class TILRecord(models.Model):
    """Time in Lieu records - tracks TIL earned and used"""
    TIL_TYPE_CHOICES = [
        ('EARNED_EARLY', 'Earned - Manager-Approved Early Start'),
        ('EARNED_OT', 'Earned - Manager-Approved Overtime'),
        ('USED', 'Used - TIL Leave'),
        ('ADJUSTED', 'Manual Adjustment'),
    ]

    STATUS_CHOICES = [
        ('PENDING', 'Pending Approval'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]

    employee = models.ForeignKey(
        EmployeeProfile,
        on_delete=models.CASCADE,
        related_name='til_records',
        help_text='Employee'
    )

    til_type = models.CharField(max_length=20, choices=TIL_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')

    # Hours earned/used (positive for earned, negative for used)
    hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text='Positive for earned, negative for used'
    )

    # Reference to attendance record (if applicable)
    daily_summary = models.ForeignKey(
        DailySummary,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='til_records',
        help_text='Related daily summary'
    )

    # Date and reason
    date = models.DateField(help_text='Date TIL was earned/used')
    reason = models.TextField(help_text='Reason for TIL')

    # Approval workflow
    requested_by = models.ForeignKey(
        EmployeeProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='til_requests',
        help_text='Who requested this TIL'
    )
    approved_by = models.ForeignKey(
        EmployeeProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='til_approvals',
        help_text='Manager who approved/rejected'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'TIL Record'
        verbose_name_plural = 'TIL Records'
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.employee.employee_name} - {self.get_til_type_display()} ({self.hours}h) - {self.get_status_display()}"


class TILBalance(models.Model):
    """Cached TIL balance per employee for quick lookups"""
    employee = models.OneToOneField(
        EmployeeProfile,
        on_delete=models.CASCADE,
        related_name='til_balance',
        help_text='Employee'
    )

    # Balance tracking
    total_earned = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        help_text='Total hours earned'
    )
    total_used = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        help_text='Total hours used'
    )
    current_balance = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        help_text='Current balance (earned - used)'
    )

    # Metadata
    last_calculated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'TIL Balance'
        verbose_name_plural = 'TIL Balances'
        ordering = ['employee__employee_name']

    def __str__(self):
        return f"{self.employee.employee_name} - {self.current_balance}h"

    def recalculate(self):
        """Recalculate balance from approved TIL records"""
        from decimal import Decimal
        from django.db.models import Sum

        approved_records = self.employee.til_records.filter(status='APPROVED')

        # Calculate earned (positive hours)
        earned = approved_records.filter(
            til_type__in=['EARNED_EARLY', 'EARNED_OT']
        ).aggregate(total=Sum('hours'))['total'] or Decimal('0')

        # Calculate used (negative hours, so we take absolute value)
        used = approved_records.filter(
            til_type='USED'
        ).aggregate(total=Sum('hours'))['total'] or Decimal('0')

        # Calculate adjustments
        adjusted = approved_records.filter(
            til_type='ADJUSTED'
        ).aggregate(total=Sum('hours'))['total'] or Decimal('0')

        self.total_earned = earned + adjusted
        self.total_used = abs(used)  # Store as positive number
        self.current_balance = self.total_earned - self.total_used
        self.save()


class PINHistory(models.Model):
    """Audit trail for PIN changes"""
    CHANGE_REASON_CHOICES = [
        ('SELF_CHANGE', 'Employee Self-Change'),
        ('HR_RESET', 'HR Reset'),
        ('INITIAL_SETUP', 'Initial Setup'),
    ]

    employee = models.ForeignKey(
        EmployeeProfile,
        on_delete=models.CASCADE,
        related_name='pin_history',
        help_text='Employee'
    )

    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='pin_changes_made',
        help_text='User who made the change'
    )

    change_reason = models.CharField(
        max_length=50,
        choices=CHANGE_REASON_CHOICES,
        help_text='Reason for PIN change'
    )

    old_pin_hash = models.CharField(max_length=128, blank=True)
    new_pin_hash = models.CharField(max_length=128)

    changed_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        verbose_name = 'PIN History'
        verbose_name_plural = 'PIN History'
        ordering = ['-changed_at']

    def __str__(self):
        return f"{self.employee.employee_name} - {self.get_change_reason_display()} at {self.changed_at}"


from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from unfold.decorators import display
from unfold.contrib.filters.admin import RangeDateFilter, RangeDateTimeFilter

from .models import (
    # V1
    EmployeeRegistry, AttendanceTap, DailySummary,
    TimesheetEdit, EmailLog, SystemSettings,
    AttendanceReport, LeaveRecord,

    # V2
    Department, Shift, EmployeeProfile,
    ShiftAssignment, TILRecord, TILBalance,
    PINHistory
)

from . import views


# ============================================================================
# V1 ADMINS (UNCHANGED BEHAVIOUR)
# ============================================================================

@admin.register(EmployeeRegistry)
class EmployeeRegistryAdmin(ModelAdmin):
    list_display = ['employee_id', 'employee_name', 'email', 'show_nfc_status', 'show_active_status', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['employee_id', 'employee_name', 'email', 'nfc_id']
    readonly_fields = ['created_at']
    list_filter_submit = True

    fieldsets = (
        ('Basic Information', {
            'fields': ('employee_id', 'employee_name', 'email', 'is_active')
        }),
        ('Authentication', {
            'fields': ('pin_code', 'nfc_id'),
        }),
        ('Metadata', {
            'fields': ('created_at',),
        }),
    )

    @display(description="NFC", label=True)
    def show_nfc_status(self, obj):
        return "✓" if obj.nfc_id else "—"

    @display(description="Status", label=True)
    def show_active_status(self, obj):
        return "Active" if obj.is_active else "Inactive"


@admin.register(AttendanceTap)
class AttendanceTapAdmin(ModelAdmin):
    list_display = ['employee_name', 'employee_id', 'action', 'timestamp']
    list_filter = [('timestamp', RangeDateTimeFilter), 'action']
    search_fields = ['employee_id', 'employee_name']
    readonly_fields = ['timestamp', 'created_at']
    list_filter_submit = True


@admin.register(DailySummary)
class DailySummaryAdmin(ModelAdmin):
    list_display = [
        'employee_name', 'date',
        'first_clock_in', 'last_clock_out',
        'show_final_hours', 'current_status', 'tap_count'
    ]

    list_filter = [('date', RangeDateFilter), 'current_status']
    search_fields = [
        'employee_id', 'employee_name',
        'selected_employee__employee_id',
        'selected_employee__employee_name'
    ]

    autocomplete_fields = ['selected_employee']
    readonly_fields = [
        'employee_id', 'employee_name',
        'raw_hours', 'break_deduction',
        'final_hours', 'tap_count'
    ]

    list_filter_submit = True

    fieldsets = (
        ('Employee', {
            'fields': ('selected_employee', 'employee_id', 'employee_name', 'date')
        }),
        ('Times', {
            'fields': ('first_clock_in', 'last_clock_out', 'current_status')
        }),
        ('Calculated', {
            'fields': ('raw_hours', 'break_deduction', 'final_hours', 'tap_count')
        }),
    )

    @display(description="Hours")
    def show_final_hours(self, obj):
        return f"{obj.final_hours}h" if obj.final_hours else "0h"


@admin.register(TimesheetEdit)
class TimesheetEditAdmin(ModelAdmin):
    list_display = ['employee_name', 'date', 'field_changed', 'edited_by', 'edited_at']
    list_filter = [('edited_at', RangeDateTimeFilter), 'field_changed']
    search_fields = ['employee_id', 'employee_name']
    readonly_fields = ['edited_at']
    list_filter_submit = True


@admin.register(EmailLog)
class EmailLogAdmin(ModelAdmin):
    list_display = ['email_type', 'recipient', 'employee_id', 'status', 'timestamp']
    list_filter = ['status', 'email_type', ('timestamp', RangeDateTimeFilter)]
    search_fields = ['recipient', 'employee_id']
    readonly_fields = ['timestamp']
    list_filter_submit = True


@admin.register(LeaveRecord)
class LeaveRecordAdmin(ModelAdmin):
    list_display = [
        'employee_name', 'leave_type',
        'start_date', 'end_date',
        'total_days', 'total_hours', 'status'
    ]

    list_filter = [
        'leave_type', 'status',
        ('start_date', RangeDateFilter),
        ('end_date', RangeDateFilter)
    ]

    search_fields = [
        'employee_id', 'employee_name',
        'selected_employee__employee_name',
        'employee_profile__employee_name'
    ]

    autocomplete_fields = ['selected_employee', 'employee_profile']
    readonly_fields = [
        'employee_id', 'employee_name',
        'total_days', 'total_hours',
        'created_at', 'created_by'
    ]

    list_filter_submit = True


@admin.register(SystemSettings)
class SystemSettingsAdmin(ModelAdmin):
    def has_add_permission(self, request):
        return not SystemSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AttendanceReport)
class AttendanceReportAdmin(ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        return views.reports_view(request)


# ============================================================================
# V2 ADMINS (NEW — SAFE, ISOLATED)
# ============================================================================

@admin.register(Department)
class DepartmentAdmin(ModelAdmin):
    list_display = ['code', 'name', 'manager', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'code']
    autocomplete_fields = ['manager']


@admin.register(Shift)
class ShiftAdmin(ModelAdmin):
    list_display = ['name', 'start_time', 'end_time', 'scheduled_hours', 'department', 'is_active']
    list_filter = ['department', 'is_active']
    search_fields = ['name', 'code']


@admin.register(EmployeeProfile)
class EmployeeProfileAdmin(ModelAdmin):
    list_display = ['employee_id', 'employee_name', 'role', 'department', 'is_active']
    list_filter = ['role', 'department', 'is_active']
    search_fields = ['employee_id', 'employee_name', 'email']
    autocomplete_fields = ['department', 'manager', 'default_shift']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ShiftAssignment)
class ShiftAssignmentAdmin(ModelAdmin):
    list_display = ['employee', 'shift', 'date', 'approved_by']
    list_filter = ['shift', 'date']
    autocomplete_fields = ['employee', 'shift', 'approved_by']


@admin.register(TILRecord)
class TILRecordAdmin(ModelAdmin):
    list_display = ['employee', 'til_type', 'hours', 'status', 'date']
    list_filter = ['til_type', 'status']
    autocomplete_fields = ['employee', 'approved_by']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(TILBalance)
class TILBalanceAdmin(ModelAdmin):
    list_display = ['employee', 'current_balance', 'last_calculated_at']
    readonly_fields = ['total_earned', 'total_used', 'current_balance', 'last_calculated_at']


@admin.register(PINHistory)
class PINHistoryAdmin(ModelAdmin):
    list_display = ['employee', 'change_reason', 'changed_by', 'changed_at']
    list_filter = ['change_reason']
    search_fields = ['employee__employee_name']
    readonly_fields = ['changed_at']
