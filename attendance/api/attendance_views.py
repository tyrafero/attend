"""
Attendance API views - clock in/out, daily summaries, current status
"""
from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal

from attendance.models import (
    DailySummary, AttendanceTap, Department, Shift,
    EmployeeProfile, SystemSettings
)
from .serializers import (
    ClockActionSerializer, DailySummarySerializer,
    AttendanceTapSerializer, CurrentStatusSerializer,
    DepartmentSerializer, ShiftSerializer, EmployeeProfileSerializer
)
from .permissions import IsEmployee, IsManager, IsHRAdmin


@api_view(['POST'])
@permission_classes([AllowAny])  # Allows both JWT and PIN authentication
def clock_action_view(request):
    """
    Clock in/out endpoint
    Supports dual authentication: JWT (for web) or PIN/NFC (for kiosk)
    """
    serializer = ClockActionSerializer(data=request.data, context={'request': request})

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    employee_profile = serializer.validated_data['employee_profile']
    auth_method = serializer.validated_data['authenticated_via']

    # Get today's date in Sydney timezone
    sydney_tz = timezone.get_current_timezone()
    now = timezone.now().astimezone(sydney_tz)
    today = now.date()
    current_time = now.time()

    # Check office hours
    system_settings = SystemSettings.load()
    if current_time < system_settings.office_start_time or current_time > system_settings.office_end_time:
        return Response({
            'error': f'Clock in/out only allowed between {system_settings.office_start_time} and {system_settings.office_end_time}'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Get or create daily summary
    daily_summary, created = DailySummary.objects.get_or_create(
        date=today,
        employee_id=employee_profile.employee_id,
        defaults={
            'employee_name': employee_profile.employee_name,
            'current_status': 'OUT',
            'tap_count': 0
        }
    )

    # Determine action (IN or OUT) based on tap count
    tap_count = daily_summary.tap_count
    action = 'IN' if tap_count % 2 == 0 else 'OUT'

    # Create attendance tap
    tap = AttendanceTap.objects.create(
        employee_id=employee_profile.employee_id,
        employee_name=employee_profile.employee_name,
        action=action,
        notes=f'Authenticated via {auth_method}'
    )

    # Update daily summary
    daily_summary.tap_count += 1
    daily_summary.current_status = action

    if action == 'IN':
        if not daily_summary.first_clock_in:
            daily_summary.first_clock_in = current_time
    else:  # OUT
        daily_summary.last_clock_out = current_time

        # Calculate hours if both clock in and out exist
        if daily_summary.first_clock_in:
            first_in_dt = datetime.combine(today, daily_summary.first_clock_in)
            last_out_dt = datetime.combine(today, daily_summary.last_clock_out)
            time_diff = last_out_dt - first_in_dt
            daily_summary.raw_hours = Decimal(time_diff.total_seconds() / 3600)

            # Apply break deduction
            if daily_summary.raw_hours > 5:
                daily_summary.break_deduction = system_settings.break_duration_hours
            else:
                daily_summary.break_deduction = Decimal('0')

            daily_summary.final_hours = daily_summary.raw_hours - daily_summary.break_deduction

    daily_summary.save()

    # Prepare response
    response_data = {
        'success': True,
        'action': action,
        'employee_id': employee_profile.employee_id,
        'employee_name': employee_profile.employee_name,
        'timestamp': tap.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        'time': current_time.strftime('%H:%M:%S'),
        'hours_worked': str(daily_summary.final_hours) if daily_summary.final_hours else None,
        'authenticated_via': auth_method,
        'message': f'Successfully clocked {action.lower()}'
    }

    return Response(response_data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsEmployee])
def current_status_view(request):
    """
    Get current user's attendance status for today
    """
    employee_profile = request.user.employee_profile
    today = timezone.now().date()

    try:
        daily_summary = DailySummary.objects.get(
            date=today,
            employee_id=employee_profile.employee_id
        )

        status_data = {
            'employee_id': employee_profile.employee_id,
            'employee_name': employee_profile.employee_name,
            'date': today,
            'current_status': daily_summary.current_status,
            'first_clock_in': daily_summary.first_clock_in,
            'last_clock_out': daily_summary.last_clock_out,
            'hours_worked': daily_summary.final_hours,
            'tap_count': daily_summary.tap_count
        }

        serializer = CurrentStatusSerializer(status_data)
        return Response(serializer.data, status=status.HTTP_200_OK)

    except DailySummary.DoesNotExist:
        return Response({
            'employee_id': employee_profile.employee_id,
            'employee_name': employee_profile.employee_name,
            'date': today,
            'current_status': 'OUT',
            'first_clock_in': None,
            'last_clock_out': None,
            'hours_worked': 0,
            'tap_count': 0
        }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsEmployee])
def my_attendance_summary_view(request):
    """
    Get current user's attendance summaries
    Supports date range filtering
    """
    employee_profile = request.user.employee_profile

    # Get date range from query params
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')

    queryset = DailySummary.objects.filter(employee_id=employee_profile.employee_id)

    if start_date:
        queryset = queryset.filter(date__gte=start_date)
    if end_date:
        queryset = queryset.filter(date__lte=end_date)
    else:
        # Default to last 30 days
        queryset = queryset.filter(date__gte=timezone.now().date() - timedelta(days=30))

    queryset = queryset.order_by('-date')

    serializer = DailySummarySerializer(queryset, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


# ViewSets for CRUD operations

class DepartmentViewSet(viewsets.ModelViewSet):
    """Department CRUD"""
    queryset = Department.objects.all().order_by('name')
    serializer_class = DepartmentSerializer

    def get_permissions(self):
        """HR only for create/update/delete, employees can view"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsHRAdmin()]
        return [IsEmployee()]


class ShiftViewSet(viewsets.ModelViewSet):
    """Shift CRUD"""
    queryset = Shift.objects.filter(is_active=True).order_by('start_time')
    serializer_class = ShiftSerializer

    def get_permissions(self):
        """HR only for create/update/delete, employees can view"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsHRAdmin()]
        return [IsEmployee()]


class EmployeeProfileViewSet(viewsets.ReadOnlyModelViewSet):
    """Employee profile list/detail (read-only via API)"""
    queryset = EmployeeProfile.objects.filter(is_active=True).select_related(
        'user', 'department', 'manager', 'default_shift'
    ).order_by('employee_name')
    serializer_class = EmployeeProfileSerializer
    permission_classes = [IsEmployee]

    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user's profile"""
        serializer = self.get_serializer(request.user.employee_profile)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsManager])
    def team(self, request):
        """Get team members (for managers)"""
        employee_profile = request.user.employee_profile
        team_members = EmployeeProfile.objects.filter(
            manager=employee_profile,
            is_active=True
        )
        serializer = self.get_serializer(team_members, many=True)
        return Response(serializer.data)


class DailySummaryViewSet(viewsets.ReadOnlyModelViewSet):
    """Daily attendance summaries (read-only)"""
    serializer_class = DailySummarySerializer
    permission_classes = [IsEmployee]

    def get_queryset(self):
        """Filter based on user role"""
        employee_profile = self.request.user.employee_profile

        # HR sees all
        if employee_profile.role == 'HR_ADMIN':
            return DailySummary.objects.all().order_by('-date')

        # Managers see their team
        if employee_profile.role == 'MANAGER':
            team_ids = employee_profile.team_members.values_list('employee_id', flat=True)
            return DailySummary.objects.filter(
                employee_id__in=list(team_ids) + [employee_profile.employee_id]
            ).order_by('-date')

        # Employees see only their own
        return DailySummary.objects.filter(
            employee_id=employee_profile.employee_id
        ).order_by('-date')


class AttendanceTapViewSet(viewsets.ReadOnlyModelViewSet):
    """Attendance taps (clock in/out history, read-only)"""
    serializer_class = AttendanceTapSerializer
    permission_classes = [IsEmployee]

    def get_queryset(self):
        """Filter based on user role"""
        employee_profile = self.request.user.employee_profile

        # HR sees all
        if employee_profile.role == 'HR_ADMIN':
            return AttendanceTap.objects.all().order_by('-timestamp')

        # Managers see their team
        if employee_profile.role == 'MANAGER':
            team_ids = employee_profile.team_members.values_list('employee_id', flat=True)
            return AttendanceTap.objects.filter(
                employee_id__in=list(team_ids) + [employee_profile.employee_id]
            ).order_by('-timestamp')

        # Employees see only their own
        return AttendanceTap.objects.filter(
            employee_id=employee_profile.employee_id
        ).order_by('-timestamp')
