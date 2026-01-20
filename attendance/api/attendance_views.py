"""
Attendance API views - clock in/out, daily summaries, current status
"""
from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes, action, authentication_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime, timedelta
from decimal import Decimal
from django_ratelimit.decorators import ratelimit

from attendance.models import (
    DailySummary, AttendanceTap, Department, Shift,
    EmployeeProfile, SystemSettings, ShiftAssignment, TILRecord, TILBalance,
    LeaveRecord
)
from attendance.services import TILService
from .serializers import (
    ClockActionSerializer, DailySummarySerializer,
    AttendanceTapSerializer, CurrentStatusSerializer,
    DepartmentSerializer, ShiftSerializer, EmployeeProfileSerializer,
    EmployeeCreateSerializer, EmployeeUpdateSerializer,
    ShiftAssignmentSerializer, TILRecordSerializer, TILBalanceSerializer,
    LeaveRecordSerializer
)
from .permissions import IsEmployee, IsManager, IsHRAdmin


@csrf_exempt
@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])  # Allows both JWT and PIN authentication
@ratelimit(key='ip', rate='30/h', method='POST', block=True)
def clock_action_view(request):
    """
    Clock in/out endpoint
    Supports dual authentication: JWT (for web) or PIN/NFC (for kiosk)
    Rate limited: 30 clock actions per hour per IP
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

    # TIL tracking data
    til_info = {}

    if action == 'IN':
        if not daily_summary.first_clock_in:
            daily_summary.first_clock_in = current_time

            # Process early bird detection using TIL service
            til_result = TILService.process_clock_in(
                employee_profile, current_time, today
            )
            til_info = {
                'is_early_bird': til_result['is_early_bird'],
                'early_minutes': til_result['early_minutes'],
                'til_earned': str(til_result['til_earned']) if til_result['til_earned'] else None,
                'til_message': til_result['message']
            }
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

        # Process overtime detection using TIL service
        til_result = TILService.process_clock_out(
            employee_profile, current_time, today, daily_summary
        )
        til_info = {
            'is_overtime': til_result['is_overtime'],
            'overtime_minutes': til_result['overtime_minutes'],
            'til_earned': str(til_result['til_earned']) if til_result['til_earned'] else None,
            'til_status': til_result['status'],
            'til_message': til_result['message']
        }

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
        'message': f'Successfully clocked {action.lower()}',
        'til': til_info
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


class EmployeeProfileViewSet(viewsets.ModelViewSet):
    """Employee profile CRUD - HR can create/update/delete, others can view"""
    queryset = EmployeeProfile.objects.select_related(
        'user', 'department', 'manager', 'default_shift'
    ).order_by('employee_name')
    permission_classes = [IsEmployee]

    def get_serializer_class(self):
        """Use different serializers for create/update"""
        if self.action == 'create':
            return EmployeeCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return EmployeeUpdateSerializer
        return EmployeeProfileSerializer

    def get_permissions(self):
        """HR only for create/update/delete, employees can view"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsHRAdmin()]
        return [IsEmployee()]

    def get_queryset(self):
        """Filter based on user role and query params"""
        queryset = super().get_queryset()

        # Show inactive employees only for HR in list view
        if self.action == 'list':
            show_inactive = self.request.query_params.get('show_inactive', 'false').lower() == 'true'
            if not show_inactive:
                queryset = queryset.filter(is_active=True)

        # Filter by department
        department = self.request.query_params.get('department')
        if department:
            queryset = queryset.filter(department_id=department)

        # Filter by role
        role = self.request.query_params.get('role')
        if role:
            queryset = queryset.filter(role=role)

        return queryset

    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user's profile"""
        serializer = EmployeeProfileSerializer(request.user.employee_profile)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsManager])
    def team(self, request):
        """Get team members (for managers) - includes direct reports AND department employees"""
        employee_profile = request.user.employee_profile
        from django.db.models import Q

        # Build query for team members
        query = Q(manager=employee_profile)  # Direct reports

        # Also include employees in departments where this user is the manager
        managed_depts = Department.objects.filter(manager=employee_profile)
        if managed_depts.exists():
            query |= Q(department__in=managed_depts)

        team_members = EmployeeProfile.objects.filter(
            query,
            is_active=True
        ).exclude(
            id=employee_profile.id  # Exclude self
        ).select_related('user', 'department', 'manager', 'default_shift').distinct()

        serializer = EmployeeProfileSerializer(team_members, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsManager])
    def team_timesheet(self, request):
        """Get timesheet data for all team members in a date range"""
        employee_profile = request.user.employee_profile
        from django.db.models import Q, Sum
        from datetime import datetime, timedelta

        # Get date range from params
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        if not start_date:
            start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')

        # Build query for team members
        query = Q(manager=employee_profile)
        managed_depts = Department.objects.filter(manager=employee_profile)
        if managed_depts.exists():
            query |= Q(department__in=managed_depts)

        team_members = EmployeeProfile.objects.filter(
            query, is_active=True
        ).exclude(id=employee_profile.id).select_related('department', 'default_shift')

        # Get attendance data for each team member
        timesheet_data = []
        for member in team_members:
            summaries = DailySummary.objects.filter(
                employee_id=member.employee_id,
                date__gte=start_date,
                date__lte=end_date
            ).order_by('date')

            total_hours = summaries.aggregate(total=Sum('final_hours'))['total'] or 0
            days_worked = summaries.filter(final_hours__gt=0).count()

            # Get daily breakdown
            daily_records = []
            for s in summaries:
                daily_records.append({
                    'date': s.date,
                    'first_clock_in': s.first_clock_in,
                    'last_clock_out': s.last_clock_out,
                    'raw_hours': float(s.raw_hours) if s.raw_hours else 0,
                    'final_hours': float(s.final_hours) if s.final_hours else 0,
                    'status': s.current_status,
                })

            timesheet_data.append({
                'employee_id': member.employee_id,
                'employee_name': member.employee_name,
                'department': member.department.name if member.department else None,
                'role': member.role,
                'email': member.user.email if member.user else None,
                'default_shift': member.default_shift.name if member.default_shift else None,
                'total_hours': float(total_hours),
                'days_worked': days_worked,
                'daily_records': daily_records,
            })

        return Response({
            'start_date': start_date,
            'end_date': end_date,
            'team_count': len(timesheet_data),
            'timesheet': timesheet_data
        })

    @action(detail=False, methods=['get'], permission_classes=[IsHRAdmin])
    def managers(self, request):
        """Get list of all managers (for assigning to employees)"""
        managers = EmployeeProfile.objects.filter(
            role__in=['MANAGER', 'HR_ADMIN'],
            is_active=True
        ).select_related('department')
        serializer = EmployeeProfileSerializer(managers, many=True)
        return Response(serializer.data)


class DailySummaryViewSet(viewsets.ReadOnlyModelViewSet):
    """Daily attendance summaries (read-only)"""
    serializer_class = DailySummarySerializer
    permission_classes = [IsEmployee]

    def get_queryset(self):
        """Filter based on user role"""
        employee_profile = self.request.user.employee_profile
        from django.db.models import Q

        # Base queryset filtered by role
        if employee_profile.role == 'HR_ADMIN':
            queryset = DailySummary.objects.all()
        elif employee_profile.role == 'MANAGER':
            # Get team members: direct reports + department employees
            query = Q(manager=employee_profile)
            managed_depts = Department.objects.filter(manager=employee_profile)
            if managed_depts.exists():
                query |= Q(department__in=managed_depts)
            team_profiles = EmployeeProfile.objects.filter(query, is_active=True)
            team_ids = list(team_profiles.values_list('employee_id', flat=True))
            queryset = DailySummary.objects.filter(
                employee_id__in=team_ids + [employee_profile.employee_id]
            )
        else:
            queryset = DailySummary.objects.filter(
                employee_id=employee_profile.employee_id
            )

        # Apply filters from query params
        employee_id = self.request.query_params.get('employee_id')
        if employee_id:
            queryset = queryset.filter(employee_id=employee_id)

        start_date = self.request.query_params.get('start_date')
        if start_date:
            queryset = queryset.filter(date__gte=start_date)

        end_date = self.request.query_params.get('end_date')
        if end_date:
            queryset = queryset.filter(date__lte=end_date)

        return queryset.order_by('-date')


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


# ============================================================================
# Phase 3: Shift Assignment and TIL ViewSets
# ============================================================================

class ShiftAssignmentViewSet(viewsets.ModelViewSet):
    """Shift assignments - managers can assign/modify, employees can view their own"""
    serializer_class = ShiftAssignmentSerializer

    def get_permissions(self):
        """Managers/HR for create/update/delete, employees can view"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsManager()]
        return [IsEmployee()]

    def get_queryset(self):
        """Filter based on user role"""
        employee_profile = self.request.user.employee_profile

        # Base queryset
        queryset = ShiftAssignment.objects.select_related(
            'employee', 'shift', 'approved_by'
        )

        # HR sees all
        if employee_profile.role == 'HR_ADMIN':
            return queryset.order_by('-date')

        # Managers see their team
        if employee_profile.role == 'MANAGER':
            team_ids = list(employee_profile.team_members.values_list('id', flat=True))
            return queryset.filter(
                employee_id__in=team_ids + [employee_profile.id]
            ).order_by('-date')

        # Employees see only their own
        return queryset.filter(employee=employee_profile).order_by('-date')

    def perform_create(self, serializer):
        """Set approved_by when manager creates assignment"""
        employee_profile = self.request.user.employee_profile
        if serializer.validated_data.get('pre_approved_early_start') or \
           serializer.validated_data.get('pre_approved_overtime'):
            serializer.save(
                approved_by=employee_profile,
                approved_at=timezone.now()
            )
        else:
            serializer.save()


class TILRecordViewSet(viewsets.ModelViewSet):
    """TIL records - employees can request, managers can approve/reject"""
    serializer_class = TILRecordSerializer

    def get_permissions(self):
        """Employees can create/view, managers can approve/reject"""
        if self.action in ['approve', 'reject']:
            return [IsManager()]
        return [IsEmployee()]

    def get_queryset(self):
        """Filter based on user role"""
        employee_profile = self.request.user.employee_profile

        queryset = TILRecord.objects.select_related(
            'employee', 'approved_by'
        )

        # HR sees all
        if employee_profile.role == 'HR_ADMIN':
            return queryset.order_by('-date')

        # Managers see their team
        if employee_profile.role == 'MANAGER':
            team_ids = list(employee_profile.team_members.values_list('id', flat=True))
            return queryset.filter(
                employee_id__in=team_ids + [employee_profile.id]
            ).order_by('-date')

        # Employees see only their own
        return queryset.filter(employee=employee_profile).order_by('-date')

    def perform_create(self, serializer):
        """Set requested_by to current user"""
        employee_profile = self.request.user.employee_profile
        serializer.save(requested_by=employee_profile)

    @action(detail=True, methods=['post'], permission_classes=[IsManager])
    def approve(self, request, pk=None):
        """Approve a TIL record"""
        til_record = self.get_object()

        if til_record.status != 'PENDING':
            return Response(
                {'error': 'Can only approve pending TIL records'},
                status=status.HTTP_400_BAD_REQUEST
            )

        til_record.status = 'APPROVED'
        til_record.approved_by = request.user.employee_profile
        til_record.approved_at = timezone.now()
        til_record.save()

        # Recalculate TIL balance
        til_balance, _ = TILBalance.objects.get_or_create(employee=til_record.employee)
        til_balance.recalculate()

        # Send approval notification email
        from attendance.tasks import send_til_approval_notification
        send_til_approval_notification.delay(til_record.id)

        return Response({'message': 'TIL approved successfully'})

    @action(detail=True, methods=['post'], permission_classes=[IsManager])
    def reject(self, request, pk=None):
        """Reject a TIL record"""
        til_record = self.get_object()

        if til_record.status != 'PENDING':
            return Response(
                {'error': 'Can only reject pending TIL records'},
                status=status.HTTP_400_BAD_REQUEST
            )

        rejection_reason = request.data.get('reason', '')

        til_record.status = 'REJECTED'
        til_record.approved_by = request.user.employee_profile
        til_record.approved_at = timezone.now()
        til_record.rejection_reason = rejection_reason
        til_record.save()

        return Response({'message': 'TIL rejected'})


@api_view(['GET'])
@permission_classes([IsEmployee])
def my_til_balance_view(request):
    """Get current user's TIL balance"""
    employee_profile = request.user.employee_profile

    til_balance, created = TILBalance.objects.get_or_create(
        employee=employee_profile
    )

    if created:
        til_balance.recalculate()

    serializer = TILBalanceSerializer(til_balance)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsManager])
def early_birds_view(request):
    """Get list of employees who clocked in early without pre-approval (Early Birds)"""
    date_str = request.query_params.get('date')
    if date_str:
        from datetime import datetime
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        date = timezone.now().date()

    # Get department filter (optional)
    department_id = request.query_params.get('department')

    early_birds = TILService.get_early_birds(date=date, department=department_id)

    return Response({
        'date': str(date),
        'count': len(early_birds),
        'early_birds': early_birds
    })


# ============================================================================
# Phase 5: Leave Management ViewSet
# ============================================================================

class LeaveRecordViewSet(viewsets.ModelViewSet):
    """Leave records - employees can apply, managers can approve/reject"""
    serializer_class = LeaveRecordSerializer

    def get_permissions(self):
        """Employees can create/view, managers can approve/reject"""
        if self.action in ['approve', 'reject', 'pending']:
            return [IsManager()]
        return [IsEmployee()]

    def get_queryset(self):
        """Filter based on user role"""
        employee_profile = self.request.user.employee_profile

        queryset = LeaveRecord.objects.select_related(
            'employee_profile', 'approved_by'
        )

        # HR sees all
        if employee_profile.role == 'HR_ADMIN':
            return queryset.order_by('-start_date')

        # Managers see their team
        if employee_profile.role == 'MANAGER':
            team_ids = list(employee_profile.team_members.values_list('id', flat=True))
            return queryset.filter(
                employee_profile_id__in=team_ids + [employee_profile.id]
            ).order_by('-start_date')

        # Employees see only their own
        return queryset.filter(employee_profile=employee_profile).order_by('-start_date')

    def perform_create(self, serializer):
        """Set employee_profile to current user"""
        serializer.save(employee_profile=self.request.user.employee_profile)

    @action(detail=False, methods=['get'], permission_classes=[IsManager])
    def pending(self, request):
        """Get pending leave requests for manager's team"""
        employee_profile = request.user.employee_profile

        if employee_profile.role == 'HR_ADMIN':
            queryset = LeaveRecord.objects.filter(status='PENDING')
        else:
            team_ids = list(employee_profile.team_members.values_list('id', flat=True))
            queryset = LeaveRecord.objects.filter(
                employee_profile_id__in=team_ids,
                status='PENDING'
            )

        queryset = queryset.select_related('employee_profile').order_by('-created_at')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsManager])
    def approve(self, request, pk=None):
        """Approve a leave request"""
        leave_record = self.get_object()

        if leave_record.status != 'PENDING':
            return Response(
                {'error': 'Can only approve pending leave requests'},
                status=status.HTTP_400_BAD_REQUEST
            )

        manager_comments = request.data.get('comments', '')

        leave_record.status = 'APPROVED'
        leave_record.approved_by = request.user.employee_profile
        leave_record.approved_at = timezone.now()
        leave_record.manager_comments = manager_comments
        leave_record.save()

        # If it's TIL leave, deduct from TIL balance
        if leave_record.leave_type == 'TIL':
            til_balance, _ = TILBalance.objects.get_or_create(
                employee=leave_record.employee_profile
            )
            # Create a TIL usage record
            TILRecord.objects.create(
                employee=leave_record.employee_profile,
                til_type='USED',
                status='APPROVED',
                hours=-leave_record.total_hours,
                date=leave_record.start_date,
                reason=f'TIL Leave: {leave_record.start_date} to {leave_record.end_date}',
                approved_by=request.user.employee_profile,
                approved_at=timezone.now()
            )
            til_balance.recalculate()

        # Send approval notification email
        from attendance.tasks import send_leave_approval_notification
        send_leave_approval_notification.delay(leave_record.id)

        return Response({'message': 'Leave approved successfully'})

    @action(detail=True, methods=['post'], permission_classes=[IsManager])
    def reject(self, request, pk=None):
        """Reject a leave request"""
        leave_record = self.get_object()

        if leave_record.status != 'PENDING':
            return Response(
                {'error': 'Can only reject pending leave requests'},
                status=status.HTTP_400_BAD_REQUEST
            )

        rejection_reason = request.data.get('reason', '')

        leave_record.status = 'REJECTED'
        leave_record.approved_by = request.user.employee_profile
        leave_record.approved_at = timezone.now()
        leave_record.rejection_reason = rejection_reason
        leave_record.save()

        # Send rejection notification email
        from attendance.tasks import send_leave_rejection_notification
        send_leave_rejection_notification.delay(leave_record.id)

        return Response({'message': 'Leave rejected'})

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a leave request (by employee)"""
        leave_record = self.get_object()

        # Only the employee who created the leave can cancel it
        if leave_record.employee_profile != request.user.employee_profile:
            return Response(
                {'error': 'You can only cancel your own leave requests'},
                status=status.HTTP_403_FORBIDDEN
            )

        if leave_record.status not in ['PENDING', 'APPROVED']:
            return Response(
                {'error': 'Can only cancel pending or approved leave requests'},
                status=status.HTTP_400_BAD_REQUEST
            )

        leave_record.status = 'CANCELLED'
        leave_record.save()

        return Response({'message': 'Leave cancelled'})
