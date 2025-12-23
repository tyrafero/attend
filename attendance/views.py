from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db.models import Sum, Count, Q
from datetime import datetime, time, timedelta
from decimal import Decimal
import pytz
import json
from .models import (
    EmployeeRegistry, AttendanceTap, DailySummary,
    TimesheetEdit, EmailLog, SystemSettings, LeaveRecord
)


# Employee Welcome Screen
def welcome_screen(request):
    """Landing page with PIN entry keypad"""
    employee_id = request.GET.get('employee_id', '')
    context = {
        'employee_id': employee_id
    }
    return render(request, 'attendance/welcome.html', context)


# Clock In/Out Processing
@require_http_methods(["POST"])
def clock_action(request):
    """Process clock in/out based on PIN or NFC"""
    pin = request.POST.get('pin', '').strip()
    nfc_id = request.POST.get('nfc_id', '').strip()

    if not pin and not nfc_id:
        return JsonResponse({'success': False, 'error': 'PIN or NFC ID is required'})

    # Find employee by PIN or NFC ID
    try:
        if nfc_id:
            employee = EmployeeRegistry.objects.get(nfc_id=nfc_id, is_active=True)
        else:
            employee = EmployeeRegistry.objects.get(pin_code=pin, is_active=True)
    except EmployeeRegistry.DoesNotExist:
        if nfc_id:
            return JsonResponse({'success': False, 'error': 'Invalid NFC card. Please register this card or use your PIN.'})
        else:
            return JsonResponse({'success': False, 'error': 'Invalid PIN'})

    # Get current time in Sydney timezone
    sydney_tz = pytz.timezone('Australia/Sydney')
    now = timezone.now().astimezone(sydney_tz)
    current_time = now.time()
    today = now.date()

    # Load system settings
    settings = SystemSettings.load()

    # Check if within allowed time (before office end time)
    if current_time >= settings.office_end_time:
        return JsonResponse({
            'success': False,
            'error': f'Clock in/out not allowed after {settings.office_end_time.strftime("%I:%M %p")}'
        })

    if current_time < settings.office_start_time:
        return JsonResponse({
            'success': False,
            'error': f'Clock in/out not allowed before {settings.office_start_time.strftime("%I:%M %p")}'
        })

    # Get or create daily summary
    daily_summary, created = DailySummary.objects.get_or_create(
        date=today,
        employee_id=employee.employee_id,
        defaults={
            'employee_name': employee.employee_name,
            'current_status': 'OUT',
            'tap_count': 0
        }
    )

    # Determine action based on tap count (even = IN, odd = OUT)
    tap_count = daily_summary.tap_count
    action = 'IN' if tap_count % 2 == 0 else 'OUT'

    # Create attendance tap
    tap = AttendanceTap.objects.create(
        employee_id=employee.employee_id,
        employee_name=employee.employee_name,
        action=action
    )

    # Update daily summary
    daily_summary.tap_count += 1
    daily_summary.current_status = action

    if action == 'IN':
        if daily_summary.first_clock_in is None:
            daily_summary.first_clock_in = current_time
    else:  # OUT
        daily_summary.last_clock_out = current_time

        # Calculate hours worked
        if daily_summary.first_clock_in:
            first_in_dt = datetime.combine(today, daily_summary.first_clock_in)
            last_out_dt = datetime.combine(today, daily_summary.last_clock_out)

            # Calculate raw hours
            time_diff = last_out_dt - first_in_dt
            raw_hours = Decimal(time_diff.total_seconds() / 3600)
            daily_summary.raw_hours = raw_hours

            # Apply break deduction if > 5 hours (use system settings)
            if raw_hours > 5:
                daily_summary.break_deduction = settings.break_duration_hours
            else:
                daily_summary.break_deduction = Decimal('0')

            daily_summary.final_hours = daily_summary.raw_hours - daily_summary.break_deduction

            # Check for early clock-out if enabled in settings
            if settings.enable_early_clockout_alerts and daily_summary.final_hours < settings.required_shift_hours:
                try:
                    from .tasks import send_early_clockout_alert
                    send_early_clockout_alert.delay(
                        employee.employee_id,
                        str(daily_summary.final_hours)
                    )
                except Exception as e:
                    # Log error but don't block clock-out
                    print(f"Failed to send early clock-out alert: {e}")

    daily_summary.save()

    # Calculate today's hours for display
    if action == 'OUT' and daily_summary.final_hours:
        hours_worked = str(daily_summary.final_hours)
    else:
        hours_worked = '0'

    return JsonResponse({
        'success': True,
        'action': action,
        'employee_name': employee.employee_name,
        'timestamp': now.strftime('%I:%M %p'),
        'hours_worked': hours_worked,
        'date': today.strftime('%B %d, %Y')
    })


# Admin Dashboard
def admin_dashboard(request):
    """Main admin dashboard with stats and employee list"""
    sydney_tz = pytz.timezone('Australia/Sydney')
    now = timezone.now().astimezone(sydney_tz)
    today = now.date()

    # Get week range (last 7 days)
    week_start = today - timedelta(days=6)

    # Get statistics
    total_employees = EmployeeRegistry.objects.filter(is_active=True).count()

    # Get today's summaries
    today_summaries = DailySummary.objects.filter(date=today)
    currently_in = today_summaries.filter(current_status='IN').count()
    currently_out = total_employees - currently_in

    # Calculate today's total hours
    total_hours = today_summaries.aggregate(
        total=Sum('final_hours')
    )['total'] or Decimal('0')

    # Calculate week's total hours
    week_summaries = DailySummary.objects.filter(date__gte=week_start, date__lte=today)
    week_hours = week_summaries.aggregate(
        total=Sum('final_hours')
    )['total'] or Decimal('0')

    # Average hours per day this week
    days_worked = week_summaries.values('date').distinct().count()
    avg_hours = (week_hours / days_worked) if days_worked > 0 else Decimal('0')

    # Get recent taps (last 10)
    recent_taps = AttendanceTap.objects.select_related().order_by('-timestamp')[:10]

    # Get employees who haven't clocked in today
    clocked_in_ids = today_summaries.values_list('employee_id', flat=True)
    not_clocked_in = EmployeeRegistry.objects.filter(
        is_active=True
    ).exclude(employee_id__in=clocked_in_ids).count()

    # Weekly chart data (last 7 days)
    chart_data = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_hours = DailySummary.objects.filter(date=day).aggregate(
            total=Sum('final_hours')
        )['total'] or Decimal('0')
        chart_data.append({
            'date': day.strftime('%a'),  # Mon, Tue, etc
            'hours': float(day_hours)
        })

    # Get all employees with their current status
    employees = EmployeeRegistry.objects.filter(is_active=True).order_by('employee_name')

    # Enrich employees with today's data
    employee_list = []
    for emp in employees:
        try:
            summary = DailySummary.objects.get(date=today, employee_id=emp.employee_id)
            emp.today_status = summary.current_status
            emp.today_hours = summary.final_hours
            emp.first_in = summary.first_clock_in
            emp.last_out = summary.last_clock_out
        except DailySummary.DoesNotExist:
            emp.today_status = 'OUT'
            emp.today_hours = Decimal('0')
            emp.first_in = None
            emp.last_out = None
        employee_list.append(emp)

    context = {
        'total_employees': total_employees,
        'currently_in': currently_in,
        'currently_out': currently_out,
        'total_hours': total_hours,
        'week_hours': week_hours,
        'avg_hours': avg_hours,
        'not_clocked_in': not_clocked_in,
        'employees': employee_list,
        'recent_taps': recent_taps,
        'chart_data': json.dumps(chart_data),  # Convert to JSON for JavaScript
        'today': today,
        'current_time': now.strftime('%I:%M %p'),
    }

    return render(request, 'attendance/admin_dashboard.html', context)


# Add Employee Page
def add_employee(request):
    """Add new employee with form validation"""
    if request.method == 'POST':
        employee_id = request.POST.get('employee_id', '').strip()
        employee_name = request.POST.get('employee_name', '').strip()
        email = request.POST.get('email', '').strip()
        pin_code = request.POST.get('pin_code', '').strip()

        errors = []

        # Validate inputs
        if not employee_id:
            errors.append('Employee ID is required')
        elif EmployeeRegistry.objects.filter(employee_id=employee_id).exists():
            errors.append('Employee ID already exists')

        if not employee_name:
            errors.append('Employee Name is required')

        if not email:
            errors.append('Email is required')

        if not pin_code:
            errors.append('PIN Code is required')
        elif len(pin_code) < 4 or len(pin_code) > 6:
            errors.append('PIN must be 4-6 digits')
        elif not pin_code.isdigit():
            errors.append('PIN must contain only digits')
        elif EmployeeRegistry.objects.filter(pin_code=pin_code).exists():
            errors.append('PIN already exists. Please choose a different PIN.')

        if errors:
            return render(request, 'attendance/add_employee.html', {
                'errors': errors,
                'employee_id': employee_id,
                'employee_name': employee_name,
                'email': email,
            })

        # Create employee
        employee = EmployeeRegistry.objects.create(
            employee_id=employee_id,
            employee_name=employee_name,
            email=email,
            pin_code=pin_code
        )

        return render(request, 'attendance/add_employee.html', {
            'success': True,
            'employee': employee
        })

    # Auto-generate next employee ID
    last_employee = EmployeeRegistry.objects.order_by('-id').first()
    if last_employee and last_employee.employee_id.startswith('EMP'):
        try:
            last_num = int(last_employee.employee_id[3:])
            next_id = f'EMP{last_num + 1:03d}'
        except ValueError:
            next_id = 'EMP001'
    else:
        next_id = 'EMP001'

    return render(request, 'attendance/add_employee.html', {
        'suggested_id': next_id
    })


# Reports View
def reports_view(request):
    """Attendance reports with filtering and date range selection"""
    sydney_tz = pytz.timezone('Australia/Sydney')
    now = timezone.now().astimezone(sydney_tz)
    today = now.date()

    # Get filter parameters
    employee_id = request.GET.get('employee_id', '')
    report_type = request.GET.get('report_type', 'daily')  # Default to today
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')

    # Calculate date range based on report type
    if report_type == 'daily':
        date_start = today
        date_end = today
    elif report_type == 'weekly':
        date_start = today - timedelta(days=6)
        date_end = today
    elif report_type == 'monthly':
        date_start = today.replace(day=1)
        date_end = today
    elif report_type == 'custom':
        if start_date and end_date:
            try:
                date_start = datetime.strptime(start_date, '%Y-%m-%d').date()
                date_end = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                date_start = today - timedelta(days=6)
                date_end = today
        else:
            date_start = today - timedelta(days=6)
            date_end = today
    else:
        date_start = today - timedelta(days=6)
        date_end = today

    # Build query
    summaries_query = DailySummary.objects.filter(
        date__gte=date_start,
        date__lte=date_end
    )

    # Filter by employee if specified
    if employee_id:
        summaries_query = summaries_query.filter(employee_id=employee_id)

    # Get summaries ordered by date and employee name
    summaries = summaries_query.order_by('-date', 'employee_name')

    # Query leave records for same date range and employee filter
    leave_filter = {'start_date__lte': date_end, 'end_date__gte': date_start}
    if employee_id:
        leave_filter['employee_id'] = employee_id

    leaves = LeaveRecord.objects.filter(**leave_filter).select_related('selected_employee').order_by('-start_date')

    # Calculate leave totals
    leave_totals = leaves.aggregate(
        total_leave_hours=Sum('total_hours'),
        total_leave_days=Sum('total_days')
    )

    # Calculate statistics
    total_hours = summaries.aggregate(total=Sum('final_hours'))['total'] or Decimal('0')
    total_days = summaries.values('date').distinct().count()
    total_employees = summaries.values('employee_id').distinct().count()
    avg_hours_per_day = (total_hours / total_days) if total_days > 0 else Decimal('0')

    # Group by employee for summary
    employee_summaries = {}
    for summary in summaries:
        if summary.employee_id not in employee_summaries:
            employee_summaries[summary.employee_id] = {
                'employee_name': summary.employee_name,
                'employee_id': summary.employee_id,
                'total_hours': Decimal('0'),
                'days_worked': 0,
                'records': []
            }
        employee_summaries[summary.employee_id]['total_hours'] += summary.final_hours
        employee_summaries[summary.employee_id]['days_worked'] += 1
        employee_summaries[summary.employee_id]['records'].append(summary)

    # Convert to list and calculate averages
    employee_list = []
    for emp_id, data in employee_summaries.items():
        data['avg_hours'] = data['total_hours'] / data['days_worked'] if data['days_worked'] > 0 else Decimal('0')
        employee_list.append(data)

    # Sort by employee name
    employee_list.sort(key=lambda x: x['employee_name'])

    # Get all active employees for dropdown
    all_employees = EmployeeRegistry.objects.filter(is_active=True).order_by('employee_name')

    context = {
        'summaries': summaries,
        'employee_summaries': employee_list,
        'all_employees': all_employees,
        'total_hours': total_hours,
        'total_days': total_days,
        'total_employees': total_employees,
        'avg_hours_per_day': avg_hours_per_day,
        'date_start': date_start,
        'date_end': date_end,
        'report_type': report_type,
        'selected_employee_id': employee_id,
        'start_date': start_date,
        'end_date': end_date,
        'leaves': leaves,
        'total_leave_hours': leave_totals['total_leave_hours'] or Decimal('0'),
        'total_leave_days': leave_totals['total_leave_days'] or 0,
        'total_hours_with_leaves': total_hours + (leave_totals['total_leave_hours'] or Decimal('0')),
    }

    return render(request, 'attendance/reports.html', context)


# Export to CSV
def export_csv(request):
    """Export attendance report to CSV"""
    import csv
    from django.http import HttpResponse

    sydney_tz = pytz.timezone('Australia/Sydney')
    now = timezone.now().astimezone(sydney_tz)
    today = now.date()

    # Get filter parameters (same as reports_view)
    employee_id = request.GET.get('employee_id', '')
    report_type = request.GET.get('report_type', 'daily')  # Default to today
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')

    # Calculate date range
    if report_type == 'daily':
        date_start = today
        date_end = today
    elif report_type == 'weekly':
        date_start = today - timedelta(days=6)
        date_end = today
    elif report_type == 'monthly':
        date_start = today.replace(day=1)
        date_end = today
    elif report_type == 'custom':
        if start_date and end_date:
            try:
                date_start = datetime.strptime(start_date, '%Y-%m-%d').date()
                date_end = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                date_start = today - timedelta(days=6)
                date_end = today
        else:
            date_start = today - timedelta(days=6)
            date_end = today
    else:
        date_start = today - timedelta(days=6)
        date_end = today

    # Build query
    summaries_query = DailySummary.objects.filter(
        date__gte=date_start,
        date__lte=date_end
    )

    if employee_id:
        summaries_query = summaries_query.filter(employee_id=employee_id)

    summaries = summaries_query.order_by('date', 'employee_name')

    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    filename = f'attendance_report_{date_start}_{date_end}.csv'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)

    # Write header
    writer.writerow([
        'Date',
        'Employee ID',
        'Employee Name',
        'First Clock In',
        'Last Clock Out',
        'Raw Hours',
        'Break Deduction',
        'Final Hours',
        'Status',
        'Tap Count'
    ])

    # Write data rows
    for summary in summaries:
        writer.writerow([
            summary.date.strftime('%Y-%m-%d'),
            summary.employee_id,
            summary.employee_name,
            summary.first_clock_in.strftime('%H:%M') if summary.first_clock_in else '',
            summary.last_clock_out.strftime('%H:%M') if summary.last_clock_out else '',
            str(summary.raw_hours),
            str(summary.break_deduction),
            str(summary.final_hours),
            summary.get_current_status_display(),
            summary.tap_count
        ])

    # Add leave records section
    writer.writerow([])  # Blank line
    writer.writerow(['LEAVE RECORDS'])
    writer.writerow([
        'Employee ID',
        'Employee Name',
        'Leave Type',
        'Start Date',
        'End Date',
        'Total Days',
        'Total Hours',
        'Reason'
    ])

    # Query and write leave records
    leave_filter = {'start_date__lte': date_end, 'end_date__gte': date_start}
    if employee_id:
        leave_filter['employee_id'] = employee_id

    leaves = LeaveRecord.objects.filter(**leave_filter).order_by('start_date')

    for leave in leaves:
        writer.writerow([
            leave.employee_id,
            leave.employee_name,
            leave.get_leave_type_display(),
            leave.start_date.strftime('%Y-%m-%d'),
            leave.end_date.strftime('%Y-%m-%d'),
            leave.total_days,
            float(leave.total_hours),
            leave.reason
        ])

    return response


# Export to PDF
def export_pdf(request):
    """Export attendance report to PDF"""
    from django.http import HttpResponse
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from io import BytesIO

    sydney_tz = pytz.timezone('Australia/Sydney')
    now = timezone.now().astimezone(sydney_tz)
    today = now.date()

    # Get filter parameters
    employee_id = request.GET.get('employee_id', '')
    report_type = request.GET.get('report_type', 'daily')  # Default to today
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')

    # Calculate date range
    if report_type == 'daily':
        date_start = today
        date_end = today
    elif report_type == 'weekly':
        date_start = today - timedelta(days=6)
        date_end = today
    elif report_type == 'monthly':
        date_start = today.replace(day=1)
        date_end = today
    elif report_type == 'custom':
        if start_date and end_date:
            try:
                date_start = datetime.strptime(start_date, '%Y-%m-%d').date()
                date_end = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                date_start = today - timedelta(days=6)
                date_end = today
        else:
            date_start = today - timedelta(days=6)
            date_end = today
    else:
        date_start = today - timedelta(days=6)
        date_end = today

    # Build query
    summaries_query = DailySummary.objects.filter(
        date__gte=date_start,
        date__lte=date_end
    )

    if employee_id:
        summaries_query = summaries_query.filter(employee_id=employee_id)

    summaries = summaries_query.order_by('date', 'employee_name')

    # Create PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), topMargin=0.5*inch)

    # Container for PDF elements
    elements = []

    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#1a365d'),
        spaceAfter=12,
        alignment=1  # Center
    )

    # Title
    title = Paragraph(f'Attendance Report<br/>{date_start.strftime("%B %d, %Y")} - {date_end.strftime("%B %d, %Y")}', title_style)
    elements.append(title)
    elements.append(Spacer(1, 0.2*inch))

    # Statistics
    total_hours = summaries.aggregate(total=Sum('final_hours'))['total'] or Decimal('0')
    total_employees = summaries.values('employee_id').distinct().count()

    stats_data = [
        ['Total Employees:', str(total_employees), 'Total Hours:', f'{total_hours:.2f}h']
    ]
    stats_table = Table(stats_data, colWidths=[1.5*inch, 1*inch, 1.5*inch, 1*inch])
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f7fafc')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2d3748')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(stats_table)
    elements.append(Spacer(1, 0.3*inch))

    # Table data
    data = [['Date', 'Employee ID', 'Employee Name', 'Clock In', 'Clock Out', 'Raw Hours', 'Break', 'Final Hours', 'Status']]

    for summary in summaries:
        data.append([
            summary.date.strftime('%Y-%m-%d'),
            summary.employee_id,
            summary.employee_name[:20],  # Truncate long names
            summary.first_clock_in.strftime('%H:%M') if summary.first_clock_in else '-',
            summary.last_clock_out.strftime('%H:%M') if summary.last_clock_out else '-',
            f'{summary.raw_hours:.2f}h',
            f'{summary.break_deduction:.2f}h',
            f'{summary.final_hours:.2f}h',
            summary.get_current_status_display()
        ])

    # Create table
    table = Table(data, colWidths=[0.9*inch, 0.9*inch, 1.5*inch, 0.8*inch, 0.8*inch, 0.9*inch, 0.7*inch, 0.9*inch, 0.8*inch])
    table.setStyle(TableStyle([
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2d3748')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),

        # Data rows
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#2d3748')),
        ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 4),

        # Grid
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),

        # Alternating row colors
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7fafc')]),
    ]))

    elements.append(table)

    # Add leave records section
    from reportlab.lib.colors import HexColor

    leave_filter = {'start_date__lte': date_end, 'end_date__gte': date_start}
    if employee_id:
        leave_filter['employee_id'] = employee_id

    leaves = LeaveRecord.objects.filter(**leave_filter).order_by('start_date')

    if leaves.exists():
        elements.append(Spacer(1, 0.3*inch))
        leave_title = Paragraph('Leave Records', styles['Heading2'])
        elements.append(leave_title)
        elements.append(Spacer(1, 0.1*inch))

        leave_data = [['Employee', 'Type', 'Start Date', 'End Date', 'Days', 'Hours']]
        for leave in leaves:
            leave_data.append([
                leave.employee_name[:20],
                leave.get_leave_type_display(),
                leave.start_date.strftime('%Y-%m-%d'),
                leave.end_date.strftime('%Y-%m-%d'),
                str(leave.total_days),
                f'{leave.total_hours}h'
            ])

        leave_table = Table(leave_data, colWidths=[1.5*inch, 1*inch, 1*inch, 1*inch, 0.7*inch, 0.8*inch])
        leave_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#48bb78')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), HexColor('#f0fdf4')),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#2d3748')),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        elements.append(leave_table)

    # Build PDF
    doc.build(elements)

    # Get PDF from buffer
    pdf = buffer.getvalue()
    buffer.close()

    # Create response
    response = HttpResponse(content_type='application/pdf')
    filename = f'attendance_report_{date_start}_{date_end}.pdf'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write(pdf)

    return response
