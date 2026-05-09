"""
Custom permission classes for role-based access control
"""
from rest_framework import permissions
import logging

logger = logging.getLogger(__name__)


class IsEmployee(permissions.BasePermission):
    """
    Permission check: User must be authenticated and have an employee profile
    (Employee, Manager, or HR/Admin role)
    """
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            hasattr(request.user, 'employee_profile') and
            request.user.employee_profile.is_active
        )


class IsManager(permissions.BasePermission):
    """
    Permission check: User must be Manager or HR/Admin role
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        if not hasattr(request.user, 'employee_profile'):
            return False

        profile = request.user.employee_profile
        return profile.is_active and profile.role in ['MANAGER', 'HR_ADMIN']


class IsHRAdmin(permissions.BasePermission):
    """
    Permission check: User must be HR/Admin role only
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        if not hasattr(request.user, 'employee_profile'):
            return False

        profile = request.user.employee_profile
        return profile.is_active and profile.role == 'HR_ADMIN'


class IsManagerOfEmployee(permissions.BasePermission):
    """
    Object-level permission: Check if user is the manager of the employee in question
    HR/Admin always has permission
    """
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False

        if not hasattr(request.user, 'employee_profile'):
            return False

        profile = request.user.employee_profile

        # HR/Admin has full access
        if profile.role == 'HR_ADMIN':
            return True

        # For Manager role, check if they manage this employee
        if profile.role == 'MANAGER':
            # Get the employee from the object
            employee = getattr(obj, 'employee', obj)

            # Check if this user is the employee's manager
            return employee.manager == profile

        return False


class IsSelfOrManager(permissions.BasePermission):
    """
    Object-level permission: User can access their own data or if they're the manager
    """
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False

        if not hasattr(request.user, 'employee_profile'):
            return False

        profile = request.user.employee_profile

        # HR/Admin has full access
        if profile.role == 'HR_ADMIN':
            return True

        # Get the employee from the object
        employee = getattr(obj, 'employee', obj)

        # Check if user is accessing their own data
        if employee == profile:
            return True

        # Check if user is the manager
        if profile.role == 'MANAGER' and employee.manager == profile:
            return True

        return False


def get_client_ip(request):
    """Get the client's IP address from the request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


class IPRestrictionPermission(permissions.BasePermission):
    """
    Check if user's IP address is allowed based on their employee IP restrictions
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return True  # Let other permissions handle authentication

        # Get user's IP address
        client_ip = get_client_ip(request)
        logger.info(f"User {request.user.username} accessing from IP: {client_ip}")

        # Check V1 EmployeeRegistry IP restrictions
        try:
            from attendance.models import EmployeeRegistry
            employee = EmployeeRegistry.objects.get(email=request.user.email)

            if employee.ip_restriction_enabled:
                is_allowed = employee.is_ip_allowed(client_ip)
                logger.warning(f"IP restriction check for {employee.employee_name}: "
                             f"Client IP {client_ip}, Allowed: {is_allowed}, "
                             f"Allowed IPs: {employee.allowed_ip_addresses}")

                if not is_allowed:
                    return False

        except EmployeeRegistry.DoesNotExist:
            logger.info(f"No EmployeeRegistry found for user {request.user.username}")

        # Check V2 EmployeeProfile IP restrictions
        try:
            if hasattr(request.user, 'employee_profile'):
                profile = request.user.employee_profile
                if hasattr(profile, 'ip_whitelist_enabled') and profile.ip_whitelist_enabled:
                    is_allowed = profile.is_ip_allowed(client_ip)
                    logger.warning(f"V2 IP restriction check for {profile.employee_name}: "
                                 f"Client IP {client_ip}, Allowed: {is_allowed}")

                    if not is_allowed:
                        return False
        except Exception as e:
            logger.error(f"Error checking V2 IP restrictions: {e}")

        return True

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)
