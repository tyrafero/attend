from django.contrib import admin
from django.utils.html import format_html
from django.shortcuts import redirect
from django.urls import path
from unfold.admin import ModelAdmin
from unfold.decorators import display
from unfold.contrib.filters.admin import RangeDateFilter, RangeDateTimeFilter
from .models import (
    EmployeeRegistry, AttendanceTap, DailySummary,
    TimesheetEdit, EmailLog, SystemSettings, AttendanceReport
)
from . import views


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
        ('Authentication Methods', {
            'fields': ('pin_code', 'nfc_id'),
            'description': 'Employee can use either PIN or NFC card to clock in/out'
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
    list_display = ['employee_name', 'employee_id', 'show_action', 'timestamp']
    list_filter = [
        'action',
        ('timestamp', RangeDateTimeFilter),  # Date/time range filter
    ]
    search_fields = ['employee_id', 'employee_name']
    readonly_fields = ['timestamp', 'created_at']
    # date_hierarchy = 'timestamp'  # Disabled - requires MySQL timezone tables
    list_filter_submit = True

    @display(description="Action", label=True)
    def show_action(self, obj):
        return obj.action


@admin.register(DailySummary)
class DailySummaryAdmin(ModelAdmin):
    list_display = ['employee_name', 'date', 'first_clock_in', 'last_clock_out',
                    'show_final_hours', 'show_status', 'tap_count']
    list_filter = [
        ('date', RangeDateFilter),  # Date range filter
        'current_status',
    ]
    search_fields = ['employee_id', 'employee_name']
    # date_hierarchy = 'date'  # Disabled - requires MySQL timezone tables
    list_filter_submit = True

    @display(description="Hours Worked", label=False)
    def show_final_hours(self, obj):
        if obj.final_hours:
            return f"{obj.final_hours}h"
        return "0h"

    @display(description="Status", label=True)
    def show_status(self, obj):
        return obj.current_status


@admin.register(TimesheetEdit)
class TimesheetEditAdmin(ModelAdmin):
    list_display = ['employee_name', 'date', 'field_changed', 'edited_by', 'edited_at']
    list_filter = [
        ('edited_at', RangeDateTimeFilter),  # Date/time range filter
        'field_changed',
    ]
    search_fields = ['employee_id', 'employee_name']
    readonly_fields = ['edited_at']
    list_filter_submit = True


@admin.register(EmailLog)
class EmailLogAdmin(ModelAdmin):
    list_display = ['email_type', 'recipient', 'employee_id', 'show_status', 'timestamp']
    list_filter = [
        'status',
        'email_type',
        ('timestamp', RangeDateTimeFilter),  # Date/time range filter
    ]
    search_fields = ['recipient', 'employee_id']
    readonly_fields = ['timestamp']
    # date_hierarchy = 'timestamp'  # Disabled - requires MySQL timezone tables
    list_filter_submit = True

    @display(description="Status", label=True)
    def show_status(self, obj):
        return obj.status


@admin.register(SystemSettings)
class SystemSettingsAdmin(ModelAdmin):
    """Admin interface for system-wide settings (singleton)"""

    fieldsets = (
        ('Office Hours', {
            'fields': ('office_start_time', 'office_end_time'),
            'description': 'Define when employees can clock in/out'
        }),
        ('Shift Configuration', {
            'fields': ('required_shift_hours', 'break_duration_hours'),
            'description': 'Configure shift duration and break time'
        }),
        ('Auto Clock-Out', {
            'fields': ('enable_auto_clockout', 'auto_clockout_interval'),
            'description': 'Automatically clock out employees at end of shift or office hours'
        }),
        ('Email Notifications', {
            'fields': (
                'enable_weekly_reports',
                'weekly_report_day',
                'weekly_report_time',
                'enable_early_clockout_alerts',
            ),
            'description': 'Configure automated email notifications'
        }),
    )

    def has_add_permission(self, request):
        # Only allow one instance (singleton pattern)
        return not SystemSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of settings
        return False


@admin.register(AttendanceReport)
class AttendanceReportAdmin(ModelAdmin):
    """Admin interface for Attendance Reports"""

    def has_add_permission(self, request):
        # Don't show "Add" button
        return False

    def has_delete_permission(self, request, obj=None):
        # No delete functionality
        return False

    def has_change_permission(self, request, obj=None):
        # No change functionality
        return False

    def changelist_view(self, request, extra_context=None):
        """Redirect to reports page when clicking on Attendance Reports"""
        return views.reports_view(request)
