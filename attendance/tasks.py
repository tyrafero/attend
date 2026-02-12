from celery import shared_task
from django.core.mail import send_mail
from django.utils import timezone
from django.conf import settings
from django.db import connection
from datetime import datetime, time, timedelta
from decimal import Decimal
import pytz
import logging
from .models import (
    EmployeeRegistry, AttendanceTap, DailySummary, EmailLog, SystemSettings, LeaveRecord, TILRecord
)

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def auto_clock_out_check(self):
    """
    Auto clock-out employees after required shift hours OR at office closing time (whichever comes first)
    Controlled by SystemSettings
    """
    try:
        connection.close()  # Close stale connections

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

        clocked_out = 0

        for summary in employees_in:
            should_clock_out = False

            # Check if it's office closing time or later
            if current_time >= system_settings.office_end_time:
                should_clock_out = True

            # Check if required shift hours have passed since first clock in
            elif summary.first_clock_in:
                # FIX: make datetime timezone-aware
                first_in_dt = sydney_tz.localize(datetime.combine(today, summary.first_clock_in))
                hours_elapsed = (now - first_in_dt).total_seconds() / 3600

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
                # FIX: make both datetimes timezone-aware
                first_in_dt = sydney_tz.localize(datetime.combine(today, summary.first_clock_in))
                last_out_dt = sydney_tz.localize(datetime.combine(today, summary.last_clock_out))
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

                clocked_out += 1

                # Email notifications disabled - only weekly summaries are sent
                # send_auto_clockout_notification.delay(summary.employee_id, str(current_time))

        logger.info(f"Auto clock-out completed. Checked: {employees_in.count()}, Clocked out: {clocked_out}")
        return f"Auto clock-out check completed. {clocked_out} employees clocked out."

    except Exception as e:
        logger.error(f"Auto clock-out failed: {e}")
        raise self.retry(exc=e, countdown=300)


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
def send_leave_notification(leave_record_id):
    """Send email notification when leave is created"""
    from django.core.mail import EmailMultiAlternatives
    from django.template.loader import render_to_string
    from django.conf import settings as django_settings

    try:
        leave_record = LeaveRecord.objects.get(id=leave_record_id)
        employee = leave_record.selected_employee

        if not employee or not employee.email:
            return f"No email for employee {leave_record.employee_id}"

        # Render email template
        html_content = render_to_string('attendance/emails/leave_notification.html', {
            'employee_name': employee.employee_name,
            'leave_record': leave_record,
            'leave_type_display': leave_record.get_leave_type_display(),
            'dates_list': leave_record.get_dates_list(),
        })

        # Plain text fallback
        text_content = f"""
Leave Approved

Hello {employee.employee_name},

Your leave has been approved:

Leave Type: {leave_record.get_leave_type_display()}
Start Date: {leave_record.start_date.strftime('%A, %B %d, %Y')}
End Date: {leave_record.end_date.strftime('%A, %B %d, %Y')}
Total Days: {leave_record.total_days}
Total Hours: {leave_record.total_hours}
Reason: {leave_record.reason or 'N/A'}

This leave will count toward your worked hours.
        """

        # Send email
        msg = EmailMultiAlternatives(
            subject=f'Leave Approved - {leave_record.get_leave_type_display()}',
            body=text_content,
            from_email=django_settings.DEFAULT_FROM_EMAIL,
            to=[employee.email]
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()

        # Log success
        EmailLog.objects.create(
            email_type='LEAVE_NOTIFICATION',
            recipient=employee.email,
            employee_id=employee.employee_id,
            status='SUCCESS',
            details=f'Leave notification sent for {leave_record.leave_type} from {leave_record.start_date} to {leave_record.end_date}'
        )

        return f"Leave notification sent to {employee.email}"

    except LeaveRecord.DoesNotExist:
        return f"LeaveRecord {leave_record_id} not found"
    except Exception as e:
        # Log failure
        EmailLog.objects.create(
            email_type='LEAVE_NOTIFICATION',
            recipient=employee.email if 'employee' in locals() else 'unknown',
            employee_id=leave_record.employee_id if 'leave_record' in locals() else 'unknown',
            status='FAILED',
            details=f'Error: {str(e)}'
        )
        logger.error(f"Failed to send leave notification: {e}")
        return f"Failed: {str(e)}"


@shared_task
def send_leave_approval_notification(leave_record_id):
    """Send email notification when leave is approved"""
    from django.core.mail import EmailMultiAlternatives
    from attendance.models import LeaveRecord, EmployeeProfile

    try:
        leave_record = LeaveRecord.objects.get(id=leave_record_id)
        employee = leave_record.employee_profile

        if not employee or not employee.user or not employee.user.email:
            return f"No email found for leave record {leave_record_id}"

        subject = f'✅ Leave Approved - {leave_record.get_leave_type_display()}'

        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #10B981 0%, #059669 100%); padding: 20px; text-align: center;">
                <h1 style="color: white; margin: 0;">Leave Approved</h1>
            </div>
            <div style="padding: 30px; background: #f9fafb;">
                <p style="font-size: 16px;">Hello <strong>{employee.employee_name}</strong>,</p>
                <p style="font-size: 16px;">Great news! Your leave request has been <strong style="color: #10B981;">approved</strong>.</p>

                <div style="background: white; border-radius: 8px; padding: 20px; margin: 20px 0; border-left: 4px solid #10B981;">
                    <h3 style="margin-top: 0; color: #374151;">Leave Details</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px 0; color: #6b7280;">Type:</td>
                            <td style="padding: 8px 0; font-weight: bold;">{leave_record.get_leave_type_display()}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #6b7280;">From:</td>
                            <td style="padding: 8px 0; font-weight: bold;">{leave_record.start_date.strftime('%A, %d %B %Y')}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #6b7280;">To:</td>
                            <td style="padding: 8px 0; font-weight: bold;">{leave_record.end_date.strftime('%A, %d %B %Y')}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #6b7280;">Duration:</td>
                            <td style="padding: 8px 0; font-weight: bold;">{leave_record.total_days} day(s) ({leave_record.total_hours}h)</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #6b7280;">Approved By:</td>
                            <td style="padding: 8px 0; font-weight: bold;">{leave_record.approved_by.employee_name if leave_record.approved_by else 'Manager'}</td>
                        </tr>
                    </table>
                    {f'<p style="margin-top: 15px; padding: 10px; background: #f0fdf4; border-radius: 4px;"><strong>Manager Comment:</strong> {leave_record.manager_comments}</p>' if leave_record.manager_comments else ''}
                </div>

                <p style="color: #6b7280; font-size: 14px;">Enjoy your time off!</p>
            </div>
            <div style="background: #1f2937; padding: 15px; text-align: center;">
                <p style="color: #9ca3af; margin: 0; font-size: 12px;">Digital Cinema Attendance System</p>
            </div>
        </div>
        """

        text_content = f"""
Leave Approved

Hello {employee.employee_name},

Your leave request has been approved.

Leave Details:
- Type: {leave_record.get_leave_type_display()}
- From: {leave_record.start_date}
- To: {leave_record.end_date}
- Duration: {leave_record.total_days} day(s)
- Approved By: {leave_record.approved_by.employee_name if leave_record.approved_by else 'Manager'}

{f'Manager Comment: {leave_record.manager_comments}' if leave_record.manager_comments else ''}

Enjoy your time off!

Digital Cinema Attendance System
        """

        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[employee.user.email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()

        EmailLog.objects.create(
            email_type='LEAVE_APPROVAL',
            recipient=employee.user.email,
            employee_id=employee.employee_id,
            status='SUCCESS',
            details=f'Leave approval notification sent for {leave_record.leave_type}'
        )

        return f"Leave approval notification sent to {employee.user.email}"

    except LeaveRecord.DoesNotExist:
        return f"LeaveRecord {leave_record_id} not found"
    except Exception as e:
        logger.error(f"Failed to send leave approval notification: {e}")
        return f"Failed: {str(e)}"


@shared_task
def send_leave_rejection_notification(leave_record_id):
    """Send email notification when leave is rejected"""
    from django.core.mail import EmailMultiAlternatives
    from attendance.models import LeaveRecord, EmployeeProfile

    try:
        leave_record = LeaveRecord.objects.get(id=leave_record_id)
        employee = leave_record.employee_profile

        if not employee or not employee.user or not employee.user.email:
            return f"No email found for leave record {leave_record_id}"

        subject = f'❌ Leave Request Declined - {leave_record.get_leave_type_display()}'

        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #EF4444 0%, #DC2626 100%); padding: 20px; text-align: center;">
                <h1 style="color: white; margin: 0;">Leave Request Declined</h1>
            </div>
            <div style="padding: 30px; background: #f9fafb;">
                <p style="font-size: 16px;">Hello <strong>{employee.employee_name}</strong>,</p>
                <p style="font-size: 16px;">Unfortunately, your leave request has been <strong style="color: #EF4444;">declined</strong>.</p>

                <div style="background: white; border-radius: 8px; padding: 20px; margin: 20px 0; border-left: 4px solid #EF4444;">
                    <h3 style="margin-top: 0; color: #374151;">Leave Details</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px 0; color: #6b7280;">Type:</td>
                            <td style="padding: 8px 0; font-weight: bold;">{leave_record.get_leave_type_display()}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #6b7280;">Requested Dates:</td>
                            <td style="padding: 8px 0; font-weight: bold;">{leave_record.start_date.strftime('%d %b')} - {leave_record.end_date.strftime('%d %b %Y')}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #6b7280;">Reviewed By:</td>
                            <td style="padding: 8px 0; font-weight: bold;">{leave_record.approved_by.employee_name if leave_record.approved_by else 'Manager'}</td>
                        </tr>
                    </table>
                    {f'<p style="margin-top: 15px; padding: 10px; background: #fef2f2; border-radius: 4px; color: #991b1b;"><strong>Reason:</strong> {leave_record.rejection_reason}</p>' if leave_record.rejection_reason else ''}
                </div>

                <p style="color: #6b7280; font-size: 14px;">If you have any questions, please speak with your manager.</p>
            </div>
            <div style="background: #1f2937; padding: 15px; text-align: center;">
                <p style="color: #9ca3af; margin: 0; font-size: 12px;">Digital Cinema Attendance System</p>
            </div>
        </div>
        """

        text_content = f"""
Leave Request Declined

Hello {employee.employee_name},

Unfortunately, your leave request has been declined.

Leave Details:
- Type: {leave_record.get_leave_type_display()}
- Requested Dates: {leave_record.start_date} - {leave_record.end_date}
- Reviewed By: {leave_record.approved_by.employee_name if leave_record.approved_by else 'Manager'}

{f'Reason: {leave_record.rejection_reason}' if leave_record.rejection_reason else ''}

If you have any questions, please speak with your manager.

Digital Cinema Attendance System
        """

        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[employee.user.email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()

        EmailLog.objects.create(
            email_type='LEAVE_REJECTION',
            recipient=employee.user.email,
            employee_id=employee.employee_id,
            status='SUCCESS',
            details=f'Leave rejection notification sent for {leave_record.leave_type}'
        )

        return f"Leave rejection notification sent to {employee.user.email}"

    except LeaveRecord.DoesNotExist:
        return f"LeaveRecord {leave_record_id} not found"
    except Exception as e:
        logger.error(f"Failed to send leave rejection notification: {e}")
        return f"Failed: {str(e)}"


@shared_task
def send_til_approval_notification(til_record_id):
    """Send email notification when TIL is approved"""
    from django.core.mail import EmailMultiAlternatives
    from attendance.models import TILRecord

    try:
        til_record = TILRecord.objects.select_related('employee', 'approved_by').get(id=til_record_id)
        employee = til_record.employee

        if not employee or not employee.user or not employee.user.email:
            return f"No email found for TIL record {til_record_id}"

        subject = f'✅ TIL {til_record.get_til_type_display()} Approved - {til_record.hours}h'

        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #8B5CF6 0%, #6D28D9 100%); padding: 20px; text-align: center;">
                <h1 style="color: white; margin: 0;">TIL Approved</h1>
            </div>
            <div style="padding: 30px; background: #f9fafb;">
                <p style="font-size: 16px;">Hello <strong>{employee.employee_name}</strong>,</p>
                <p style="font-size: 16px;">Your Time in Lieu request has been <strong style="color: #8B5CF6;">approved</strong>.</p>

                <div style="background: white; border-radius: 8px; padding: 20px; margin: 20px 0; border-left: 4px solid #8B5CF6;">
                    <h3 style="margin-top: 0; color: #374151;">TIL Details</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px 0; color: #6b7280;">Type:</td>
                            <td style="padding: 8px 0; font-weight: bold;">{til_record.get_til_type_display()}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #6b7280;">Hours:</td>
                            <td style="padding: 8px 0; font-weight: bold; color: #10B981;">+{til_record.hours}h</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #6b7280;">Date:</td>
                            <td style="padding: 8px 0; font-weight: bold;">{til_record.date.strftime('%A, %d %B %Y')}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #6b7280;">Approved By:</td>
                            <td style="padding: 8px 0; font-weight: bold;">{til_record.approved_by.employee_name if til_record.approved_by else 'Manager'}</td>
                        </tr>
                    </table>
                </div>

                <p style="color: #6b7280; font-size: 14px;">Your TIL balance has been updated.</p>
            </div>
            <div style="background: #1f2937; padding: 15px; text-align: center;">
                <p style="color: #9ca3af; margin: 0; font-size: 12px;">Digital Cinema Attendance System</p>
            </div>
        </div>
        """

        text_content = f"""
TIL Approved

Hello {employee.employee_name},

Your Time in Lieu request has been approved.

TIL Details:
- Type: {til_record.get_til_type_display()}
- Hours: +{til_record.hours}h
- Date: {til_record.date}
- Approved By: {til_record.approved_by.employee_name if til_record.approved_by else 'Manager'}

Your TIL balance has been updated.

Digital Cinema Attendance System
        """

        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[employee.user.email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()

        EmailLog.objects.create(
            email_type='TIL_APPROVAL',
            recipient=employee.user.email,
            employee_id=employee.employee_id,
            status='SUCCESS',
            details=f'TIL approval notification sent for {til_record.hours}h'
        )

        return f"TIL approval notification sent to {employee.user.email}"

    except TILRecord.DoesNotExist:
        return f"TILRecord {til_record_id} not found"
    except Exception as e:
        logger.error(f"Failed to send TIL approval notification: {e}")
        return f"Failed: {str(e)}"


@shared_task
def send_til_request_notification_to_manager(til_record_id):
    """Send email notification to manager when TIL is requested"""
    from django.core.mail import EmailMultiAlternatives
    from attendance.models import TILRecord, EmployeeProfile
    from django.conf import settings as django_settings

    try:
        til_record = TILRecord.objects.select_related('employee', 'employee__manager').get(id=til_record_id)
        employee = til_record.employee

        # Get manager
        manager = employee.manager
        if not manager or not manager.user or not manager.user.email:
            # Try to get department manager
            if employee.department and employee.department.manager:
                manager = employee.department.manager
            else:
                return f"No manager found for employee {employee.employee_name}"

        if not manager.user or not manager.user.email:
            return f"Manager {manager.employee_name} has no email"

        # Get frontend URL
        frontend_url = getattr(django_settings, 'FRONTEND_URL', 'http://localhost:5173')
        portal_link = f"{frontend_url}/til"

        subject = f'TIL Request - {employee.employee_name}'

        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #8B5CF6 0%, #6D28D9 100%); padding: 20px; text-align: center;">
                <h1 style="color: white; margin: 0;">TIL Request</h1>
            </div>
            <div style="padding: 30px; background: #f9fafb;">
                <p style="font-size: 16px;">Hello <strong>{manager.employee_name}</strong>,</p>
                <p style="font-size: 16px;"><strong>{employee.employee_name}</strong> has submitted a Time in Lieu (TIL) request that requires your approval.</p>

                <div style="background: white; border-radius: 8px; padding: 20px; margin: 20px 0; border-left: 4px solid #8B5CF6;">
                    <h3 style="margin-top: 0; color: #374151;">TIL Details</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px 0; color: #6b7280;">Employee:</td>
                            <td style="padding: 8px 0; font-weight: bold;">{employee.employee_name}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #6b7280;">Type:</td>
                            <td style="padding: 8px 0; font-weight: bold;">{til_record.get_til_type_display()}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #6b7280;">Hours:</td>
                            <td style="padding: 8px 0; font-weight: bold; color: #10B981;">{til_record.hours}h</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #6b7280;">Date:</td>
                            <td style="padding: 8px 0; font-weight: bold;">{til_record.date.strftime('%A, %d %B %Y')}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #6b7280;">Reason:</td>
                            <td style="padding: 8px 0;">{til_record.reason or 'N/A'}</td>
                        </tr>
                    </table>
                </div>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="{portal_link}" style="display: inline-block; background: linear-gradient(135deg, #8B5CF6 0%, #6D28D9 100%); color: white; padding: 12px 30px; text-decoration: none; border-radius: 8px; font-weight: bold;">
                        Review in Manager Portal
                    </a>
                </div>

                <p style="color: #6b7280; font-size: 14px;">Please review and approve or reject this request in the manager portal.</p>
            </div>
            <div style="background: #1f2937; padding: 15px; text-align: center;">
                <p style="color: #9ca3af; margin: 0; font-size: 12px;">Digital Cinema Attendance System</p>
            </div>
        </div>
        """

        text_content = f"""
TIL Request

Hello {manager.employee_name},

{employee.employee_name} has submitted a Time in Lieu (TIL) request that requires your approval.

TIL Details:
- Employee: {employee.employee_name}
- Type: {til_record.get_til_type_display()}
- Hours: {til_record.hours}h
- Date: {til_record.date}
- Reason: {til_record.reason or 'N/A'}

Please review this request at: {portal_link}

Digital Cinema Attendance System
        """

        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[manager.user.email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()

        EmailLog.objects.create(
            email_type='TIL_REQUEST_TO_MANAGER',
            recipient=manager.user.email,
            employee_id=employee.employee_id,
            status='SUCCESS',
            details=f'TIL request notification sent to manager {manager.employee_name}'
        )

        return f"TIL request notification sent to {manager.user.email}"

    except TILRecord.DoesNotExist:
        return f"TILRecord {til_record_id} not found"
    except Exception as e:
        logger.error(f"Failed to send TIL request notification: {e}")
        return f"Failed: {str(e)}"


@shared_task
def send_leave_request_notification_to_manager(leave_record_id):
    """Send email notification to manager when leave is requested"""
    from django.core.mail import EmailMultiAlternatives
    from attendance.models import LeaveRecord, EmployeeProfile
    from django.conf import settings as django_settings

    try:
        leave_record = LeaveRecord.objects.select_related(
            'employee_profile', 'employee_profile__manager'
        ).get(id=leave_record_id)
        employee = leave_record.employee_profile

        if not employee:
            return f"No employee profile found for leave record {leave_record_id}"

        # Get manager
        manager = employee.manager
        if not manager or not manager.user or not manager.user.email:
            # Try to get department manager
            if employee.department and employee.department.manager:
                manager = employee.department.manager
            else:
                return f"No manager found for employee {employee.employee_name}"

        if not manager.user or not manager.user.email:
            return f"Manager {manager.employee_name} has no email"

        # Get frontend URL
        frontend_url = getattr(django_settings, 'FRONTEND_URL', 'http://localhost:5173')
        portal_link = f"{frontend_url}/leave"

        subject = f'Leave Request - {employee.employee_name}'

        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #3B82F6 0%, #1D4ED8 100%); padding: 20px; text-align: center;">
                <h1 style="color: white; margin: 0;">Leave Request</h1>
            </div>
            <div style="padding: 30px; background: #f9fafb;">
                <p style="font-size: 16px;">Hello <strong>{manager.employee_name}</strong>,</p>
                <p style="font-size: 16px;"><strong>{employee.employee_name}</strong> has submitted a leave request that requires your approval.</p>

                <div style="background: white; border-radius: 8px; padding: 20px; margin: 20px 0; border-left: 4px solid #3B82F6;">
                    <h3 style="margin-top: 0; color: #374151;">Leave Details</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px 0; color: #6b7280;">Employee:</td>
                            <td style="padding: 8px 0; font-weight: bold;">{employee.employee_name}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #6b7280;">Leave Type:</td>
                            <td style="padding: 8px 0; font-weight: bold;">{leave_record.get_leave_type_display()}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #6b7280;">From:</td>
                            <td style="padding: 8px 0; font-weight: bold;">{leave_record.start_date.strftime('%A, %d %B %Y')}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #6b7280;">To:</td>
                            <td style="padding: 8px 0; font-weight: bold;">{leave_record.end_date.strftime('%A, %d %B %Y')}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #6b7280;">Duration:</td>
                            <td style="padding: 8px 0; font-weight: bold;">{leave_record.total_days} day(s) ({leave_record.total_hours}h)</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #6b7280;">Reason:</td>
                            <td style="padding: 8px 0;">{leave_record.reason or 'N/A'}</td>
                        </tr>
                    </table>
                </div>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="{portal_link}" style="display: inline-block; background: linear-gradient(135deg, #3B82F6 0%, #1D4ED8 100%); color: white; padding: 12px 30px; text-decoration: none; border-radius: 8px; font-weight: bold;">
                        Review in Manager Portal
                    </a>
                </div>

                <p style="color: #6b7280; font-size: 14px;">Please review and approve or reject this request in the manager portal.</p>
            </div>
            <div style="background: #1f2937; padding: 15px; text-align: center;">
                <p style="color: #9ca3af; margin: 0; font-size: 12px;">Digital Cinema Attendance System</p>
            </div>
        </div>
        """

        text_content = f"""
Leave Request

Hello {manager.employee_name},

{employee.employee_name} has submitted a leave request that requires your approval.

Leave Details:
- Employee: {employee.employee_name}
- Leave Type: {leave_record.get_leave_type_display()}
- From: {leave_record.start_date}
- To: {leave_record.end_date}
- Duration: {leave_record.total_days} day(s) ({leave_record.total_hours}h)
- Reason: {leave_record.reason or 'N/A'}

Please review this request at: {portal_link}

Digital Cinema Attendance System
        """

        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[manager.user.email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()

        EmailLog.objects.create(
            email_type='LEAVE_REQUEST_TO_MANAGER',
            recipient=manager.user.email,
            employee_id=employee.employee_id,
            status='SUCCESS',
            details=f'Leave request notification sent to manager {manager.employee_name}'
        )

        return f"Leave request notification sent to {manager.user.email}"

    except LeaveRecord.DoesNotExist:
        return f"LeaveRecord {leave_record_id} not found"
    except Exception as e:
        logger.error(f"Failed to send leave request notification: {e}")
        return f"Failed: {str(e)}"


@shared_task
def send_weekly_reports():
    """
    Send beautiful HTML weekly reports every Friday after 5 PM
    """
    from django.core.mail import EmailMultiAlternatives
    from django.template.loader import render_to_string
    from django.conf import settings as django_settings
    from django.db.models import Avg, Sum

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

    # Calculate weekly awards
    early_bird = None
    overtime_champion = None

    # Get all summaries for this week
    all_summaries = DailySummary.objects.filter(
        date__gte=monday,
        date__lte=friday
    )

    # Calculate Early Bird (earliest average clock-in time)
    employee_avg_clock_in = {}
    for emp in employees:
        emp_summaries = all_summaries.filter(
            employee_id=emp.employee_id,
            first_clock_in__isnull=False
        )
        if emp_summaries.exists():
            # Calculate average clock-in time in seconds since midnight
            total_seconds = 0
            count = 0
            for summary in emp_summaries:
                if summary.first_clock_in:
                    seconds = summary.first_clock_in.hour * 3600 + \
                             summary.first_clock_in.minute * 60 + \
                             summary.first_clock_in.second
                    total_seconds += seconds
                    count += 1
            if count > 0:
                avg_seconds = total_seconds / count
                employee_avg_clock_in[emp.employee_id] = {
                    'name': emp.employee_name,
                    'avg_seconds': avg_seconds,
                    'avg_time': timedelta(seconds=avg_seconds)
                }

    if employee_avg_clock_in:
        earliest_emp_id = min(employee_avg_clock_in.keys(),
                             key=lambda x: employee_avg_clock_in[x]['avg_seconds'])
        early_bird = {
            'name': employee_avg_clock_in[earliest_emp_id]['name'],
            'avg_time': str(employee_avg_clock_in[earliest_emp_id]['avg_time']).split('.')[0]
        }

    # Calculate Overtime Champion (most total hours worked)
    employee_total_hours = {}
    for emp in employees:
        total = all_summaries.filter(
            employee_id=emp.employee_id
        ).aggregate(total_hours=Sum('final_hours'))['total_hours'] or Decimal('0')

        if total > 0:
            employee_total_hours[emp.employee_id] = {
                'name': emp.employee_name,
                'total_hours': total
            }

    if employee_total_hours:
        champion_emp_id = max(employee_total_hours.keys(),
                             key=lambda x: employee_total_hours[x]['total_hours'])
        overtime_champion = {
            'name': employee_total_hours[champion_emp_id]['name'],
            'total_hours': f"{employee_total_hours[champion_emp_id]['total_hours']:.1f}"
        }

    sent_count = 0

    # Send individual reports
    for employee in employees:
        # Get this week's attendance records
        summaries = DailySummary.objects.filter(
            employee_id=employee.employee_id,
            date__gte=monday,
            date__lte=friday
        ).order_by('date')

        # Get this week's leave records
        emp_leaves = LeaveRecord.objects.filter(
            employee_id=employee.employee_id,
            start_date__lte=friday,
            end_date__gte=monday
        )

        # Calculate leave hours for the week
        leave_hours = Decimal('0')
        leave_days = 0
        for leave in emp_leaves:
            # For each leave, count only the days that fall within this week
            current_day = max(leave.start_date, monday)
            end_day = min(leave.end_date, friday)
            while current_day <= end_day:
                if current_day.weekday() < 5:  # Monday-Friday
                    leave_hours += leave.hours_per_day
                    leave_days += 1
                current_day += timedelta(days=1)

        # Build daily breakdown including leaves
        daily_breakdown = []
        current_day = monday
        while current_day <= friday:
            day_summary = summaries.filter(date=current_day).first()
            day_leave = emp_leaves.filter(
                start_date__lte=current_day,
                end_date__gte=current_day
            ).first()

            daily_breakdown.append({
                'date': current_day,
                'attendance': day_summary,
                'leave': day_leave,
            })
            current_day += timedelta(days=1)

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
            'early_bird': early_bird,
            'overtime_champion': overtime_champion,
            'leave_records': emp_leaves,
            'leave_hours': f"{leave_hours:.1f}",
            'leave_days': leave_days,
            'total_hours_with_leaves': f"{(total_hours + leave_hours):.1f}",
            'daily_breakdown': daily_breakdown,
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
