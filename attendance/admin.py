from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from unfold.decorators import display
from .models import (
    EmployeeRegistry, AttendanceTap, DailySummary,
    TimesheetEdit, EmailLog, SystemSettings
)


@admin.register(EmployeeRegistry)
class EmployeeRegistryAdmin(ModelAdmin):
    list_display = ['employee_id', 'employee_name', 'email', 'show_active_status', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['employee_id', 'employee_name', 'email']
    readonly_fields = ['created_at']
    list_filter_submit = True

    @display(description="Status", label=True)
    def show_active_status(self, obj):
        return "Active" if obj.is_active else "Inactive"


@admin.register(AttendanceTap)
class AttendanceTapAdmin(ModelAdmin):
    list_display = ['employee_name', 'employee_id', 'show_action', 'timestamp']
    list_filter = ['action', 'timestamp']
    search_fields = ['employee_id', 'employee_name']
    readonly_fields = ['timestamp', 'created_at']
    date_hierarchy = 'timestamp'
    list_filter_submit = True

    @display(description="Action", label=True)
    def show_action(self, obj):
        return obj.action


@admin.register(DailySummary)
class DailySummaryAdmin(ModelAdmin):
    list_display = ['employee_name', 'date', 'first_clock_in', 'last_clock_out',
                    'show_final_hours', 'show_status', 'tap_count']
    list_filter = ['date', 'current_status']
    search_fields = ['employee_id', 'employee_name']
    date_hierarchy = 'date'
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
    list_filter = ['edited_at', 'field_changed']
    search_fields = ['employee_id', 'employee_name']
    readonly_fields = ['edited_at']
    list_filter_submit = True


@admin.register(EmailLog)
class EmailLogAdmin(ModelAdmin):
    list_display = ['email_type', 'recipient', 'employee_id', 'show_status', 'timestamp']
    list_filter = ['status', 'email_type', 'timestamp']
    search_fields = ['recipient', 'employee_id']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'
    list_filter_submit = True

    @display(description="Status", label=True)
    def show_status(self, obj):
        return obj.status


@admin.register(SystemSettings)
class SystemSettingsAdmin(ModelAdmin):
    list_display = ['key', 'value', 'description']
    search_fields = ['key', 'description']
    list_filter_submit = True
