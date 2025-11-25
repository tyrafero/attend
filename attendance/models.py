from django.db import models
from django.contrib.auth.models import User


class EmployeeRegistry(models.Model):
    employee_id = models.CharField(max_length=50, unique=True)  # EMP123
    employee_name = models.CharField(max_length=200)
    email = models.EmailField()
    pin_code = models.CharField(max_length=6)  # 4-6 digit PIN
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Employee'
        verbose_name_plural = 'Employees'
        ordering = ['employee_name']

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
