"""
Custom permission classes for role-based access control
"""
from rest_framework import permissions


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
