"""
API Views for authentication and user management
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from django.contrib.auth.hashers import make_password
from django.utils import timezone

from .serializers import (
    LoginSerializer,
    PINLoginSerializer,
    UserSerializer,
    ChangePINSerializer,
    ResetPINSerializer,
)
from .permissions import IsEmployee, IsHRAdmin
from attendance.models import EmployeeProfile, PINHistory


def get_tokens_for_user(user):
    """Generate JWT tokens for user"""
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """
    Username/password login endpoint
    Returns JWT tokens and user data
    """
    serializer = LoginSerializer(data=request.data)

    if serializer.is_valid():
        user = serializer.validated_data['user']

        # Generate JWT tokens
        tokens = get_tokens_for_user(user)

        # Serialize user data
        user_data = UserSerializer(user).data

        return Response({
            'user': user_data,
            'access': tokens['access'],
            'refresh': tokens['refresh'],
        }, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def pin_login_view(request):
    """
    PIN-based login endpoint (for kiosk mode)
    Returns JWT tokens and user data
    """
    serializer = PINLoginSerializer(data=request.data)

    if serializer.is_valid():
        user = serializer.validated_data['user']
        employee_profile = serializer.validated_data['employee_profile']

        # Generate JWT tokens
        tokens = get_tokens_for_user(user)

        # Serialize user data
        user_data = UserSerializer(user).data

        return Response({
            'user': user_data,
            'access': tokens['access'],
            'refresh': tokens['refresh'],
            'message': f'Welcome, {employee_profile.employee_name}!'
        }, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    Logout endpoint - blacklists the refresh token
    """
    try:
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response(
                {'error': 'Refresh token is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        token = RefreshToken(refresh_token)
        token.blacklist()

        return Response(
            {'message': 'Successfully logged out'},
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([IsEmployee])
def current_user_view(request):
    """
    Get current authenticated user's profile
    """
    user = request.user
    user_data = UserSerializer(user).data
    return Response(user_data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsEmployee])
def change_pin_view(request):
    """
    Change employee's PIN (requires old PIN verification)
    """
    serializer = ChangePINSerializer(data=request.data, context={'request': request})

    if serializer.is_valid():
        employee_profile = serializer.validated_data['employee_profile']
        new_pin = serializer.validated_data['new_pin']

        # Store old PIN hash for history
        old_pin_hash = employee_profile.pin_hash

        # Hash and save new PIN
        employee_profile.pin_hash = make_password(new_pin)
        employee_profile.pin_updated_at = timezone.now()
        employee_profile.save()

        # Create PIN history record
        PINHistory.objects.create(
            employee=employee_profile,
            changed_by=request.user,
            change_reason='SELF_CHANGE',
            old_pin_hash=old_pin_hash,
            new_pin_hash=employee_profile.pin_hash,
            ip_address=get_client_ip(request)
        )

        return Response(
            {'message': 'PIN changed successfully'},
            status=status.HTTP_200_OK
        )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsHRAdmin])
def reset_pin_view(request):
    """
    HR/Admin can reset any employee's PIN
    """
    serializer = ResetPINSerializer(data=request.data)

    if serializer.is_valid():
        employee_id = serializer.validated_data['employee_id']
        new_pin = serializer.validated_data['new_pin']

        try:
            employee_profile = EmployeeProfile.objects.get(id=employee_id)
        except EmployeeProfile.DoesNotExist:
            return Response(
                {'error': 'Employee not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Store old PIN hash for history
        old_pin_hash = employee_profile.pin_hash

        # Hash and save new PIN
        employee_profile.pin_hash = make_password(new_pin)
        employee_profile.pin_updated_at = timezone.now()
        employee_profile.save()

        # Create PIN history record
        PINHistory.objects.create(
            employee=employee_profile,
            changed_by=request.user,
            change_reason='HR_RESET',
            old_pin_hash=old_pin_hash,
            new_pin_hash=employee_profile.pin_hash,
            ip_address=get_client_ip(request)
        )

        return Response(
            {'message': f'PIN reset successfully for {employee_profile.employee_name}'},
            status=status.HTTP_200_OK
        )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsEmployee])
def change_password_view(request):
    """
    Change user's password (requires old password verification)
    """
    old_password = request.data.get('old_password')
    new_password = request.data.get('new_password')

    if not old_password or not new_password:
        return Response(
            {'error': 'Both old_password and new_password are required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    user = request.user

    # Verify old password
    if not user.check_password(old_password):
        return Response(
            {'old_password': ['Incorrect password']},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Validate new password length
    if len(new_password) < 6:
        return Response(
            {'new_password': ['Password must be at least 6 characters']},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Set new password
    user.set_password(new_password)
    user.save()

    return Response(
        {'message': 'Password changed successfully'},
        status=status.HTTP_200_OK
    )


def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
