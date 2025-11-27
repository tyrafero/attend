from celery import shared_task
from django.core.mail import send_mail
from django.utils import timezone
from django.conf import settings
from datetime import datetime, time, timedelta
from decimal import Decimal
import pytz
from .models import (
    EmployeeRegistry, AttendanceTap, DailySummary, EmailLog, SystemSettings
)


@shared_task
def auto_clock_out_check():
    """
    Auto clock-out employees after required shift hours OR at office closing time (whichever comes first)
    Controlled by SystemSettings
    """
    # Load system settings
    system_settings = SystemSettings.load()

    # Check if auto clock-out is enabled
    if not system_settings.enable_auto_clockout:
        return "Auto clock-out is disabled in system settings"

    sydney_tz = pytz.timezone('Australia/Sydney')
    now = timezone.now().astimezone(sydney_tz)
    today = now.date()
    current_time = now.time()

    # Get all employees currently clocked IN
    employees_in = DailySummary.objects.filter(
        date=today,
        current_status='IN'
    )

    for summary in employees_in:
        should_clock_out = False

        # Check if it's office closing time or later
        if current_time >= system_settings.office_end_time:
            should_clock_out = True

        # Check if required shift hours have passed since first clock in
        elif summary.first_clock_in:
            first_in_dt = datetime.combine(today, summary.first_clock_in)
            hours_elapsed = (now - sydney_tz.localize(first_in_dt)).total_seconds() / 3600

            if hours_elapsed >= float(system_settings.required_shift_hours):
                should_clock_out = True

        if should_clock_out:
            # Create auto clock-out tap
            AttendanceTap.objects.create(
                employee_id=summary.employee_id,
                employee_name=summary.employee_name,
                action='OUT',
                notes='Auto clock-out'
            )

            # Update daily summary
            summary.last_clock_out = current_time
            summary.tap_count += 1
            summary.current_status = 'OUT'

            # Calculate hours
            first_in_dt = datetime.combine(today, summary.first_clock_in)
            last_out_dt = datetime.combine(today, summary.last_clock_out)
            time_diff = last_out_dt - first_in_dt
            raw_hours = Decimal(time_diff.total_seconds() / 3600)
            summary.raw_hours = raw_hours

            # Apply break deduction (use system settings)
            if raw_hours > 5:
                summary.break_deduction = system_settings.break_duration_hours
            else:
                summary.break_deduction = Decimal('0')

            summary.final_hours = summary.raw_hours - summary.break_deduction
            summary.save()

            # Email notifications disabled - only weekly summaries are sent
            # send_auto_clockout_notification.delay(summary.employee_id, str(current_time))

    return f"Auto clock-out check completed. {employees_in.count()} employees checked."


@shared_task
def send_auto_clockout_notification(employee_id, clock_out_time):
    """Send email notification for auto clock-out"""
    try:
        employee = EmployeeRegistry.objects.get(employee_id=employee_id)

        subject = 'Automatic Clock-Out Notification'
        message = f"""
Dear {employee.employee_name},

You have been automatically clocked out at {clock_out_time}.

This occurred because either:
- You have worked 8 hours, or
- It is now 5 PM

Your attendance has been recorded.

Best regards,
Attendance System
        """

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [employee.email],
            fail_silently=False,
        )

        EmailLog.objects.create(
            email_type='AUTO_CLOCKOUT',
            recipient=employee.email,
            employee_id=employee_id,
            status='SUCCESS',
            details=f'Auto clock-out notification sent at {clock_out_time}'
        )

    except Exception as e:
        EmailLog.objects.create(
            email_type='AUTO_CLOCKOUT',
            recipient=employee.email if employee else 'unknown',
            employee_id=employee_id,
            status='FAILED',
            details=str(e)
        )


@shared_task
def send_missed_clock_out_reminders():
    """
    Send reminders to employees who forgot to clock out
    Runs daily at 8 PM
    """
    sydney_tz = pytz.timezone('Australia/Sydney')
    today = timezone.now().astimezone(sydney_tz).date()

    # Find employees still clocked IN
    employees_still_in = DailySummary.objects.filter(
        date=today,
        current_status='IN'
    )

    for summary in employees_still_in:
        try:
            employee = EmployeeRegistry.objects.get(employee_id=summary.employee_id)

            subject = 'Reminder: You Forgot to Clock Out'
            message = f"""
Dear {employee.employee_name},

Our records show that you clocked in today but forgot to clock out.

Clock In Time: {summary.first_clock_in.strftime('%I:%M %p') if summary.first_clock_in else 'N/A'}

Please contact your manager to correct your timesheet.

Best regards,
Attendance System
            """

            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [employee.email],
                fail_silently=False,
            )

            EmailLog.objects.create(
                email_type='MISSED_CLOCKOUT',
                recipient=employee.email,
                employee_id=summary.employee_id,
                status='SUCCESS',
                details=f'Reminder sent for {today}'
            )

        except Exception as e:
            EmailLog.objects.create(
                email_type='MISSED_CLOCKOUT',
                recipient='unknown',
                employee_id=summary.employee_id,
                status='FAILED',
                details=str(e)
            )

    return f"Sent {employees_still_in.count()} missed clock-out reminders"


@shared_task
def send_early_clockout_alert(employee_id, hours_worked):
    """Send alert when employee clocks out before completing 8 hours"""
    try:
        employee = EmployeeRegistry.objects.get(employee_id=employee_id)

        subject = 'Early Clock-Out Alert'
        message = f"""
Dear {employee.employee_name},

You have clocked out with only {hours_worked} hours worked today.

The required shift is 8 hours (including break).

If this was intentional, no action is needed. Otherwise, please contact your manager.

Best regards,
Attendance System
        """

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [employee.email],
            fail_silently=False,
        )

        EmailLog.objects.create(
            email_type='EARLY_CLOCKOUT',
            recipient=employee.email,
            employee_id=employee_id,
            status='SUCCESS',
            details=f'Early clock-out alert sent. Hours: {hours_worked}'
        )

    except Exception as e:
        EmailLog.objects.create(
            email_type='EARLY_CLOCKOUT',
            recipient='unknown',
            employee_id=employee_id,
            status='FAILED',
            details=str(e)
        )


@shared_task
def send_weekly_reports_old():
    """
    Send weekly reports on configured day/time
    Controlled by SystemSettings
    """
    # Load system settings
    system_settings = SystemSettings.load()

    # Check if weekly reports are enabled
    if not system_settings.enable_weekly_reports:
        return "Weekly reports are disabled in system settings"

    sydney_tz = pytz.timezone('Australia/Sydney')
    today = timezone.now().astimezone(sydney_tz).date()

    # Calculate week range (Monday to Friday)
    days_since_monday = today.weekday()
    monday = today - timedelta(days=days_since_monday)
    friday = monday + timedelta(days=4)

    # Get all employees
    employees = EmployeeRegistry.objects.filter(is_active=True)

    # Send individual reports
    for employee in employees:
        summaries = DailySummary.objects.filter(
            employee_id=employee.employee_id,
            date__gte=monday,
            date__lte=friday
        ).order_by('date')

        total_hours = sum(s.final_hours for s in summaries)
        days_worked = summaries.count()

        # Build report
        report_lines = []
        for summary in summaries:
            report_lines.append(
                f"{summary.date.strftime('%A, %b %d')}: "
                f"{summary.first_clock_in.strftime('%I:%M %p') if summary.first_clock_in else 'N/A'} - "
                f"{summary.last_clock_out.strftime('%I:%M %p') if summary.last_clock_out else 'N/A'} "
                f"({summary.final_hours}h)"
            )

        subject = f'Weekly Attendance Report - Week of {monday.strftime("%b %d")}'
        message = f"""
Dear {employee.employee_name},

Here is your attendance report for the week of {monday.strftime('%B %d')} - {friday.strftime('%B %d, %Y')}:

{chr(10).join(report_lines)}

Total Hours: {total_hours}h
Days Worked: {days_worked}/5

Best regards,
Attendance System
        """

        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [employee.email],
                fail_silently=False,
            )

            EmailLog.objects.create(
                email_type='WEEKLY_REPORT',
                recipient=employee.email,
                employee_id=employee.employee_id,
                status='SUCCESS',
                details=f'Weekly report sent for {monday} to {friday}'
            )
        except Exception as e:
            EmailLog.objects.create(
                email_type='WEEKLY_REPORT',
                recipient=employee.email,
                employee_id=employee.employee_id,
                status='FAILED',
                details=str(e)
            )

    return f"Sent weekly reports to {employees.count()} employees"


@shared_task
def send_weekly_reports():
    """
    Send beautiful HTML weekly reports every Friday after 5 PM
    """
    from django.core.mail import EmailMultiAlternatives
    from django.template.loader import render_to_string
    from django.conf import settings as django_settings

    # Load system settings
    system_settings = SystemSettings.load()

    # Check if weekly reports are enabled
    if not system_settings.enable_weekly_reports:
        return "Weekly reports are disabled in system settings"

    sydney_tz = pytz.timezone('Australia/Sydney')
    today = timezone.now().astimezone(sydney_tz).date()
    current_year = today.year

    # Calculate week range (Monday to Friday)
    days_since_monday = today.weekday()
    monday = today - timedelta(days=days_since_monday)
    friday = monday + timedelta(days=4)

    # Get all active employees
    employees = EmployeeRegistry.objects.filter(is_active=True)

    sent_count = 0

    # Send individual reports
    for employee in employees:
        # Get this week's attendance records
        summaries = DailySummary.objects.filter(
            employee_id=employee.employee_id,
            date__gte=monday,
            date__lte=friday
        ).order_by('date')

        # Calculate totals
        total_hours = sum(s.final_hours for s in summaries if s.final_hours)
        days_worked = sum(1 for s in summaries if s.final_hours and s.final_hours > 0)
        avg_hours = (total_hours / days_worked) if days_worked > 0 else Decimal('0')

        # Prepare template context
        context = {
            'employee_name': employee.employee_name,
            'week_start': monday,
            'week_end': friday,
            'total_hours': f"{total_hours:.1f}",
            'days_worked': days_worked,
            'avg_hours': f"{avg_hours:.1f}",
            'records': summaries,
            'current_year': current_year,
        }

        try:
            # Render HTML email
            html_content = render_to_string('attendance/emails/weekly_report.html', context)

            # Create plain text version
            text_content = f"""
Weekly Attendance Report
{monday.strftime('%B %d')} - {friday.strftime('%B %d, %Y')}

Hello {employee.employee_name},

Total Hours: {total_hours:.1f}h
Days Worked: {days_worked}/5

Daily Breakdown:
"""
            for record in summaries:
                clock_in = record.first_clock_in.strftime('%I:%M %p') if record.first_clock_in else '—'
                clock_out = record.last_clock_out.strftime('%I:%M %p') if record.last_clock_out else '—'
                hours = f"{record.final_hours}h" if record.final_hours else '—'
                text_content += f"{record.date.strftime('%A, %b %d')}: {clock_in} - {clock_out} ({hours})\n"

            text_content += f"\nBest regards,\nDigital Cinema Attendance System"

            # Create email with both HTML and plain text
            subject = f'📊 Weekly Attendance Report - Week of {monday.strftime("%b %d")}'

            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=django_settings.DEFAULT_FROM_EMAIL,
                to=[employee.email]
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

            # Log success
            EmailLog.objects.create(
                email_type='WEEKLY_REPORT',
                recipient=employee.email,
                employee_id=employee.employee_id,
                status='SUCCESS',
                details=f'Beautiful HTML weekly report sent for {monday} to {friday}'
            )

            sent_count += 1

        except Exception as e:
            # Log failure
            EmailLog.objects.create(
                email_type='WEEKLY_REPORT',
                recipient=employee.email,
                employee_id=employee.employee_id,
                status='FAILED',
                details=str(e)
            )

    return f"Sent beautiful weekly reports to {sent_count}/{employees.count()} employees"
