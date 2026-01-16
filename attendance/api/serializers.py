"""
API Serializers for authentication and user management
"""
from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.hashers import check_password, make_password
from attendance.models import (
    EmployeeProfile, Department, Shift, DailySummary, AttendanceTap
)


class EmployeeProfileSerializer(serializers.ModelSerializer):
    """Serializer for EmployeeProfile"""
    department_name = serializers.CharField(source='department.name', read_only=True)
    manager_name = serializers.CharField(source='manager.employee_name', read_only=True, allow_null=True)

    class Meta:
        model = EmployeeProfile
        fields = [
            'id', 'employee_id', 'employee_name', 'email',
            'department', 'department_name', 'role',
            'manager', 'manager_name', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User with embedded EmployeeProfile"""
    employee_profile = EmployeeProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'employee_profile']
        read_only_fields = ['id']


class LoginSerializer(serializers.Serializer):
    """Serializer for username/password login"""
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        from django.contrib.auth import authenticate

        username = attrs.get('username')
        password = attrs.get('password')

        # Authenticate user
        user = authenticate(username=username, password=password)

        if not user:
            raise serializers.ValidationError('Invalid username or password')

        # Check if user has employee profile
        if not hasattr(user, 'employee_profile'):
            raise serializers.ValidationError('User does not have an employee profile')

        # Check if employee is active
        if not user.employee_profile.is_active:
            raise serializers.ValidationError('Employee account is inactive')

        attrs['user'] = user
        return attrs


class PINLoginSerializer(serializers.Serializer):
    """Serializer for PIN-based login (kiosk mode)"""
    pin = serializers.CharField(
        max_length=6,
        min_length=4,
        required=True,
        write_only=True
    )

    def validate_pin(self, value):
        """Validate that PIN is numeric"""
        if not value.isdigit():
            raise serializers.ValidationError('PIN must be numeric')
        return value

    def validate(self, attrs):
        pin = attrs.get('pin')

        # Find employee by PIN hash
        # We need to iterate through active employees and check password
        from attendance.models import EmployeeProfile

        for profile in EmployeeProfile.objects.filter(is_active=True).select_related('user'):
            if check_password(pin, profile.pin_hash):
                attrs['user'] = profile.user
                attrs['employee_profile'] = profile
                return attrs

        raise serializers.ValidationError('Invalid PIN')


class ChangePINSerializer(serializers.Serializer):
    """Serializer for changing PIN"""
    old_pin = serializers.CharField(max_length=6, required=True, write_only=True)
    new_pin = serializers.CharField(max_length=6, min_length=4, required=True, write_only=True)

    def validate_new_pin(self, value):
        """Validate new PIN"""
        if not value.isdigit():
            raise serializers.ValidationError('PIN must be numeric')

        return value

    def validate(self, attrs):
        old_pin = attrs.get('old_pin')
        new_pin = attrs.get('new_pin')

        # Get employee profile from context
        request = self.context.get('request')
        if not request or not hasattr(request.user, 'employee_profile'):
            raise serializers.ValidationError('User does not have an employee profile')

        profile = request.user.employee_profile

        # Verify old PIN
        if not check_password(old_pin, profile.pin_hash):
            raise serializers.ValidationError({'old_pin': 'Incorrect PIN'})

        # Check if new PIN is different from old PIN
        if old_pin == new_pin:
            raise serializers.ValidationError({'new_pin': 'New PIN must be different from old PIN'})

        attrs['employee_profile'] = profile
        return attrs


class ResetPINSerializer(serializers.Serializer):
    """Serializer for HR to reset employee PIN"""
    employee_id = serializers.IntegerField(required=True)
    new_pin = serializers.CharField(max_length=6, min_length=4, required=True, write_only=True)

    def validate_new_pin(self, value):
        """Validate new PIN"""
        if not value.isdigit():
            raise serializers.ValidationError('PIN must be numeric')
        return value

    def validate_employee_id(self, value):
        """Validate employee exists"""
        try:
            profile = EmployeeProfile.objects.get(id=value)
        except EmployeeProfile.DoesNotExist:
            raise serializers.ValidationError('Employee not found')

        return value


# ============================================================================
# Attendance Serializers
# ============================================================================

class DepartmentSerializer(serializers.ModelSerializer):
    """Serializer for Department"""
    manager_name = serializers.CharField(source='manager.employee_name', read_only=True, allow_null=True)
    employee_count = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = ['id', 'code', 'name', 'description', 'manager', 'manager_name',
                  'employee_count', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']

    def get_employee_count(self, obj):
        return obj.employees.filter(is_active=True).count()


class ShiftSerializer(serializers.ModelSerializer):
    """Serializer for Shift"""
    department_name = serializers.CharField(source='department.name', read_only=True, allow_null=True)

    class Meta:
        model = Shift
        fields = ['id', 'code', 'name', 'start_time', 'end_time', 'scheduled_hours',
                  'break_duration_hours', 'early_arrival_grace_minutes',
                  'late_departure_grace_minutes', 'department', 'department_name',
                  'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']




class AttendanceTapSerializer(serializers.ModelSerializer):
    """Serializer for AttendanceTap"""

    class Meta:
        model = AttendanceTap
        fields = ['id', 'timestamp', 'employee_id', 'employee_name',
                  'action', 'notes', 'created_at']
        read_only_fields = ['id', 'timestamp', 'created_at']


class DailySummarySerializer(serializers.ModelSerializer):
    """Serializer for DailySummary"""

    class Meta:
        model = DailySummary
        fields = [
            'id', 'date', 'employee_id', 'employee_name',
            'first_clock_in', 'last_clock_out',
            'raw_hours', 'break_deduction', 'final_hours',
            'current_status', 'tap_count'
        ]
        read_only_fields = ['id']


class ClockActionSerializer(serializers.Serializer):
    """
    Serializer for clock in/out action
    Supports both JWT authentication and PIN-based authentication
    """
    pin = serializers.CharField(max_length=6, required=False, write_only=True)
    nfc_id = serializers.CharField(max_length=100, required=False, write_only=True)

    def validate(self, attrs):
        request = self.context.get('request')

        # Check if user is authenticated via JWT
        if request and request.user.is_authenticated:
            # JWT authentication - user already authenticated
            if hasattr(request.user, 'employee_profile'):
                attrs['employee_profile'] = request.user.employee_profile
                attrs['authenticated_via'] = 'jwt'
                return attrs
            else:
                raise serializers.ValidationError('User does not have an employee profile')

        # PIN or NFC authentication (kiosk mode)
        pin = attrs.get('pin')
        nfc_id = attrs.get('nfc_id')

        if not pin and not nfc_id:
            raise serializers.ValidationError('PIN, NFC ID, or authentication token required')

        # Try PIN authentication
        if pin:
            for profile in EmployeeProfile.objects.filter(is_active=True).select_related('user'):
                if check_password(pin, profile.pin_hash):
                    attrs['employee_profile'] = profile
                    attrs['authenticated_via'] = 'pin'
                    return attrs
            raise serializers.ValidationError('Invalid PIN')

        # Try NFC authentication
        if nfc_id:
            try:
                profile = EmployeeProfile.objects.get(nfc_id=nfc_id, is_active=True)
                attrs['employee_profile'] = profile
                attrs['authenticated_via'] = 'nfc'
                return attrs
            except EmployeeProfile.DoesNotExist:
                raise serializers.ValidationError('Invalid NFC ID')

        raise serializers.ValidationError('Authentication failed')


class CurrentStatusSerializer(serializers.Serializer):
    """Serializer for current attendance status"""
    employee_id = serializers.CharField()
    employee_name = serializers.CharField()
    current_status = serializers.CharField()
    first_clock_in = serializers.TimeField(allow_null=True)
    last_clock_out = serializers.TimeField(allow_null=True)
    hours_worked = serializers.DecimalField(max_digits=5, decimal_places=2)
    tap_count = serializers.IntegerField()
    date = serializers.DateField()
