from django.contrib import admin
from .models import (
    EmployeeRegistry, AttendanceTap, DailySummary,
    TimesheetEdit, EmailLog, SystemSettings
)


@admin.register(EmployeeRegistry)
class EmployeeRegistryAdmin(admin.ModelAdmin):
    list_display = ['employee_id', 'employee_name', 'email', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['employee_id', 'employee_name', 'email']
    readonly_fields = ['created_at']


@admin.register(AttendanceTap)
class AttendanceTapAdmin(admin.ModelAdmin):
    list_display = ['employee_name', 'employee_id', 'action', 'timestamp']
    list_filter = ['action', 'timestamp']
    search_fields = ['employee_id', 'employee_name']
    readonly_fields = ['timestamp', 'created_at']
    date_hierarchy = 'timestamp'


@admin.register(DailySummary)
class DailySummaryAdmin(admin.ModelAdmin):
    list_display = ['employee_name', 'date', 'first_clock_in', 'last_clock_out',
                    'final_hours', 'current_status', 'tap_count']
    list_filter = ['date', 'current_status']
    search_fields = ['employee_id', 'employee_name']
    date_hierarchy = 'date'


@admin.register(TimesheetEdit)
class TimesheetEditAdmin(admin.ModelAdmin):
    list_display = ['employee_name', 'date', 'field_changed', 'edited_by', 'edited_at']
    list_filter = ['edited_at', 'field_changed']
    search_fields = ['employee_id', 'employee_name']
    readonly_fields = ['edited_at']


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ['email_type', 'recipient', 'employee_id', 'status', 'timestamp']
    list_filter = ['status', 'email_type', 'timestamp']
    search_fields = ['recipient', 'employee_id']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'


@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    list_display = ['key', 'value', 'description']
    search_fields = ['key', 'description']
