from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db.models import Sum, Count, Q
from datetime import datetime, time, timedelta
from decimal import Decimal
import pytz
from .models import (
    EmployeeRegistry, AttendanceTap, DailySummary,
    TimesheetEdit, EmailLog
)


# Employee Welcome Screen
def welcome_screen(request):
    """Landing page with PIN entry keypad"""
    return render(request, 'attendance/welcome.html')


# Clock In/Out Processing
@require_http_methods(["POST"])
def clock_action(request):
    """Process clock in/out based on PIN"""
    pin = request.POST.get('pin', '').strip()

    if not pin:
        return JsonResponse({'success': False, 'error': 'PIN is required'})

    # Find employee by PIN
    try:
        employee = EmployeeRegistry.objects.get(pin_code=pin, is_active=True)
    except EmployeeRegistry.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Invalid PIN'})

    # Get current time in Sydney timezone
    sydney_tz = pytz.timezone('Australia/Sydney')
    now = timezone.now().astimezone(sydney_tz)
    current_time = now.time()
    today = now.date()

    # Check if within allowed time (7 AM - 5 PM)
    if not (time(7, 0) <= current_time <= time(17, 0)):
        return JsonResponse({
            'success': False,
            'error': 'Clock in/out only allowed between 7 AM and 5 PM'
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

            # Apply break deduction if > 5 hours
            if raw_hours > 5:
                daily_summary.break_deduction = Decimal('0.5')  # 30 minutes
            else:
                daily_summary.break_deduction = Decimal('0')

            daily_summary.final_hours = daily_summary.raw_hours - daily_summary.break_deduction

            # Check for early clock-out (less than 8 hours)
            # Disabled for now - uncomment to enable early clock-out email alerts
            # if daily_summary.final_hours < 8:
            #     try:
            #         from .tasks import send_early_clockout_alert
            #         send_early_clockout_alert.delay(
            #             employee.employee_id,
            #             str(daily_summary.final_hours)
            #         )
            #     except Exception as e:
            #         # Log error but don't block clock-out
            #         print(f"Failed to send early clock-out alert: {e}")

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
    today = timezone.now().astimezone(sydney_tz).date()

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
        'employees': employee_list,
        'today': today,
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
