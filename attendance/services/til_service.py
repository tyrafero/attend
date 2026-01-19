"""
TIL (Time in Lieu) Service - Business logic for TIL calculation

Handles:
- Early bird detection (clocking in early without pre-approval)
- Pre-approved early start TIL calculation
- Overtime detection and TIL calculation
- TIL balance recalculation
"""

from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Sum

from attendance.models import (
    EmployeeProfile, DailySummary, ShiftAssignment,
    TILRecord, TILBalance, Shift
)


class TILService:
    """Service class for TIL (Time in Lieu) business logic"""

    # TIL Multiplier thresholds
    TIL_TIER1_HOURS = Decimal('3')  # First 3 hours
    TIL_TIER1_MULTIPLIER = Decimal('1.5')  # 1.5x for first 3 hours
    TIL_TIER2_MULTIPLIER = Decimal('2.0')  # 2x for hours after 3

    @staticmethod
    def calculate_til_hours(raw_hours):
        """
        Calculate TIL hours based on overtime multipliers:
        - First 3 hours: 1.5x
        - After 3 hours: 2x

        Example:
        - 2 hours OT → 2 * 1.5 = 3 hours TIL
        - 4 hours OT → (3 * 1.5) + (1 * 2) = 6.5 hours TIL
        - 5 hours OT → (3 * 1.5) + (2 * 2) = 8.5 hours TIL
        """
        raw_hours = Decimal(str(raw_hours))

        if raw_hours <= Decimal('0'):
            return Decimal('0')

        if raw_hours <= TILService.TIL_TIER1_HOURS:
            # All hours at 1.5x
            return raw_hours * TILService.TIL_TIER1_MULTIPLIER
        else:
            # First 3 hours at 1.5x, remainder at 2x
            tier1_til = TILService.TIL_TIER1_HOURS * TILService.TIL_TIER1_MULTIPLIER
            tier2_hours = raw_hours - TILService.TIL_TIER1_HOURS
            tier2_til = tier2_hours * TILService.TIL_TIER2_MULTIPLIER
            return tier1_til + tier2_til

    @staticmethod
    def get_employee_shift_for_date(employee_profile, date):
        """
        Get the employee's shift for a specific date.
        First checks ShiftAssignment, then falls back to default_shift.

        Returns: (shift, shift_assignment, effective_start_time, effective_end_time)
        """
        # Check for specific shift assignment for this date
        try:
            assignment = ShiftAssignment.objects.select_related('shift').get(
                employee=employee_profile,
                date=date
            )
            start_time = assignment.get_effective_start_time()
            end_time = assignment.get_effective_end_time()
            return (assignment.shift, assignment, start_time, end_time)
        except ShiftAssignment.DoesNotExist:
            pass

        # Fall back to default shift
        if employee_profile.default_shift:
            shift = employee_profile.default_shift
            return (shift, None, shift.start_time, shift.end_time)

        # No shift found
        return (None, None, None, None)

    @staticmethod
    def process_clock_in(employee_profile, clock_in_time, date):
        """
        Process clock in and detect early arrival.

        Returns dict with:
        - is_early_bird: True if arrived early without pre-approval
        - early_minutes: Minutes arrived early
        - pre_approved: Whether early start was pre-approved
        - til_earned: TIL hours earned (if pre-approved)
        """
        result = {
            'is_early_bird': False,
            'early_minutes': 0,
            'pre_approved': False,
            'til_earned': Decimal('0'),
            'message': None
        }

        # Get shift for this date
        shift, assignment, scheduled_start, scheduled_end = TILService.get_employee_shift_for_date(
            employee_profile, date
        )

        if not shift:
            result['message'] = 'No shift assigned - skipping early bird check'
            return result

        # Convert clock_in_time to comparable format
        if isinstance(clock_in_time, datetime):
            clock_in = clock_in_time.time()
        else:
            clock_in = clock_in_time

        # Calculate early arrival in minutes
        scheduled_start_dt = datetime.combine(date, scheduled_start)
        clock_in_dt = datetime.combine(date, clock_in)

        if clock_in_dt < scheduled_start_dt:
            early_diff = scheduled_start_dt - clock_in_dt
            early_minutes = int(early_diff.total_seconds() / 60)
            result['early_minutes'] = early_minutes

            # Check if within grace period
            grace_minutes = shift.early_arrival_grace_minutes

            if early_minutes > grace_minutes:
                # Check if pre-approved
                if assignment and assignment.pre_approved_early_start:
                    result['pre_approved'] = True
                    approved_minutes = assignment.approved_early_minutes

                    # Calculate TIL earned (up to approved amount) with multipliers
                    earned_minutes = min(early_minutes, approved_minutes)
                    raw_hours = Decimal(earned_minutes) / Decimal(60)
                    result['til_earned'] = TILService.calculate_til_hours(raw_hours)
                    result['message'] = f'Pre-approved early start: {earned_minutes} min ({raw_hours}h) = {result["til_earned"]}h TIL (with multiplier)'

                    # Auto-create approved TIL record
                    TILService.create_til_record(
                        employee=employee_profile,
                        til_type='EARNED_EARLY',
                        hours=result['til_earned'],
                        date=date,
                        reason=f'Pre-approved early start: clocked in {early_minutes} min early (approved: {approved_minutes} min)',
                        auto_approve=True,
                        approved_by=assignment.approved_by
                    )
                else:
                    # No pre-approval - mark as early bird (flagged for review)
                    result['is_early_bird'] = True
                    result['message'] = f'Early bird: {early_minutes} minutes early without pre-approval'

        return result

    @staticmethod
    def process_clock_out(employee_profile, clock_out_time, date, daily_summary=None):
        """
        Process clock out and detect overtime.

        Returns dict with:
        - is_overtime: True if worked past scheduled end
        - overtime_minutes: Minutes worked past scheduled end
        - pre_approved: Whether overtime was pre-approved
        - til_earned: TIL hours earned (if pre-approved)
        - status: 'APPROVED' or 'PENDING' for TIL record
        """
        result = {
            'is_overtime': False,
            'overtime_minutes': 0,
            'pre_approved': False,
            'til_earned': Decimal('0'),
            'status': None,
            'message': None
        }

        # Get shift for this date
        shift, assignment, scheduled_start, scheduled_end = TILService.get_employee_shift_for_date(
            employee_profile, date
        )

        if not shift:
            result['message'] = 'No shift assigned - skipping overtime check'
            return result

        # Convert clock_out_time to comparable format
        if isinstance(clock_out_time, datetime):
            clock_out = clock_out_time.time()
        else:
            clock_out = clock_out_time

        # Calculate overtime in minutes
        scheduled_end_dt = datetime.combine(date, scheduled_end)
        clock_out_dt = datetime.combine(date, clock_out)

        # Handle shifts that cross midnight
        if scheduled_end < scheduled_start:
            # Night shift - end time is next day
            scheduled_end_dt += timedelta(days=1)

        if clock_out_dt > scheduled_end_dt:
            overtime_diff = clock_out_dt - scheduled_end_dt
            overtime_minutes = int(overtime_diff.total_seconds() / 60)
            result['overtime_minutes'] = overtime_minutes

            # Check if within grace period
            grace_minutes = shift.late_departure_grace_minutes

            if overtime_minutes > grace_minutes:
                result['is_overtime'] = True

                # Check if pre-approved
                if assignment and assignment.pre_approved_overtime:
                    result['pre_approved'] = True
                    approved_hours = assignment.approved_overtime_hours

                    # Calculate TIL earned (up to approved amount) with multipliers
                    actual_ot_hours = Decimal(overtime_minutes) / Decimal(60)
                    earned_hours = min(actual_ot_hours, Decimal(str(approved_hours)))
                    result['til_earned'] = TILService.calculate_til_hours(earned_hours)
                    result['status'] = 'APPROVED'
                    result['message'] = f'Pre-approved overtime: {overtime_minutes} min ({earned_hours}h) = {result["til_earned"]}h TIL (with multiplier)'

                    # Auto-create approved TIL record
                    TILService.create_til_record(
                        employee=employee_profile,
                        til_type='EARNED_OT',
                        hours=result['til_earned'],
                        date=date,
                        reason=f'Pre-approved overtime: worked {overtime_minutes} min past end (approved: {approved_hours}h)',
                        auto_approve=True,
                        approved_by=assignment.approved_by,
                        daily_summary=daily_summary
                    )
                else:
                    # No pre-approval - create pending TIL record for manager review
                    actual_ot_hours = Decimal(overtime_minutes) / Decimal(60)
                    result['til_earned'] = TILService.calculate_til_hours(actual_ot_hours)
                    result['status'] = 'PENDING'
                    result['message'] = f'Unapproved overtime: {overtime_minutes} min ({actual_ot_hours}h) = {result["til_earned"]}h TIL (pending approval, with multiplier)'

                    # Create pending TIL record
                    TILService.create_til_record(
                        employee=employee_profile,
                        til_type='EARNED_OT',
                        hours=result['til_earned'],
                        date=date,
                        reason=f'Overtime worked: {overtime_minutes} min ({actual_ot_hours}h raw) = {result["til_earned"]}h TIL (not pre-approved)',
                        auto_approve=False,
                        daily_summary=daily_summary
                    )

        return result

    @staticmethod
    def create_til_record(employee, til_type, hours, date, reason, auto_approve=False,
                          approved_by=None, daily_summary=None):
        """
        Create a TIL record and optionally auto-approve it.
        """
        status = 'APPROVED' if auto_approve else 'PENDING'
        approved_at = timezone.now() if auto_approve else None

        til_record = TILRecord.objects.create(
            employee=employee,
            til_type=til_type,
            status=status,
            hours=hours,
            date=date,
            reason=reason,
            approved_by=approved_by,
            approved_at=approved_at,
            daily_summary=daily_summary
        )

        # Update balance if approved
        if auto_approve:
            TILService.recalculate_balance(employee)

        return til_record

    @staticmethod
    def recalculate_balance(employee):
        """
        Recalculate TIL balance for an employee based on approved records.
        """
        til_balance, created = TILBalance.objects.get_or_create(employee=employee)
        til_balance.recalculate()
        return til_balance

    @staticmethod
    def get_early_birds(date=None, department=None):
        """
        Get list of employees who clocked in early without pre-approval (Early Birds).
        Useful for manager dashboard.
        """
        if date is None:
            date = timezone.now().date()

        # Get all daily summaries for the date with first clock in
        summaries = DailySummary.objects.filter(
            date=date,
            first_clock_in__isnull=False
        )

        early_birds = []

        for summary in summaries:
            # Get employee profile
            try:
                employee = EmployeeProfile.objects.get(employee_id=summary.employee_id)
            except EmployeeProfile.DoesNotExist:
                continue

            # Filter by department if specified
            if department and employee.department_id != department:
                continue

            # Get shift info
            shift, assignment, scheduled_start, _ = TILService.get_employee_shift_for_date(
                employee, date
            )

            if not shift:
                continue

            # Calculate early arrival
            clock_in = summary.first_clock_in
            scheduled_start_dt = datetime.combine(date, scheduled_start)
            clock_in_dt = datetime.combine(date, clock_in)

            if clock_in_dt < scheduled_start_dt:
                early_diff = scheduled_start_dt - clock_in_dt
                early_minutes = int(early_diff.total_seconds() / 60)

                # Check if beyond grace period and not pre-approved
                if early_minutes > shift.early_arrival_grace_minutes:
                    is_pre_approved = assignment and assignment.pre_approved_early_start
                    if not is_pre_approved:
                        early_birds.append({
                            'employee_id': employee.employee_id,
                            'employee_name': employee.employee_name,
                            'department': employee.department.name,
                            'clock_in': clock_in,
                            'scheduled_start': scheduled_start,
                            'early_minutes': early_minutes,
                            'shift_name': shift.name
                        })

        return early_birds

    @staticmethod
    def approve_til(til_record_id, approved_by):
        """
        Approve a pending TIL record.
        """
        try:
            til_record = TILRecord.objects.get(id=til_record_id)
        except TILRecord.DoesNotExist:
            return {'success': False, 'error': 'TIL record not found'}

        if til_record.status != 'PENDING':
            return {'success': False, 'error': 'TIL record is not pending'}

        til_record.status = 'APPROVED'
        til_record.approved_by = approved_by
        til_record.approved_at = timezone.now()
        til_record.save()

        # Recalculate balance
        TILService.recalculate_balance(til_record.employee)

        return {'success': True, 'til_record': til_record}

    @staticmethod
    def reject_til(til_record_id, rejected_by, rejection_reason=''):
        """
        Reject a pending TIL record.
        """
        try:
            til_record = TILRecord.objects.get(id=til_record_id)
        except TILRecord.DoesNotExist:
            return {'success': False, 'error': 'TIL record not found'}

        if til_record.status != 'PENDING':
            return {'success': False, 'error': 'TIL record is not pending'}

        til_record.status = 'REJECTED'
        til_record.approved_by = rejected_by
        til_record.approved_at = timezone.now()
        til_record.rejection_reason = rejection_reason
        til_record.save()

        return {'success': True, 'til_record': til_record}

    @staticmethod
    def get_pending_til_count(manager):
        """
        Get count of pending TIL records for a manager's team.
        """
        team_ids = list(manager.team_members.values_list('id', flat=True))
        return TILRecord.objects.filter(
            employee_id__in=team_ids,
            status='PENDING'
        ).count()
