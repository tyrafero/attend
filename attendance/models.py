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
    ]

    # Employee selection (follows DailySummary pattern)
    selected_employee = models.ForeignKey(
        EmployeeRegistry,
        on_delete=models.CASCADE,
        related_name='leave_records',
        help_text='Select employee from dropdown'
    )

    # Denormalized fields (auto-populated)
    employee_id = models.CharField(max_length=50)
    employee_name = models.CharField(max_length=200)

    # Leave details
    leave_type = models.CharField(max_length=20, choices=LEAVE_TYPE_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True)

    # Auto-calculated fields
    hours_per_day = models.DecimalField(max_digits=4, decimal_places=2, default=8.0)
    total_days = models.IntegerField(default=0)
    total_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    # Audit trail
    created_at = models.DateTimeField(auto_now_add=True)
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

        # Auto-populate employee fields
        if self.selected_employee:
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
