"""
IP Restriction Middleware for Employee Access Control
"""
import logging
from django.http import HttpResponseForbidden
from django.contrib.auth.models import AnonymousUser
from attendance.models import EmployeeRegistry

logger = logging.getLogger(__name__)


def get_client_ip(request):
    """Get the client's IP address from the request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


class IPRestrictionMiddleware:
    """
    Middleware to check IP restrictions for authenticated users
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip IP check for non-authenticated users and admin URLs
        if isinstance(request.user, AnonymousUser) or request.path.startswith('/admin/'):
            return self.get_response(request)

        # Get client IP
        client_ip = get_client_ip(request)

        if request.user.is_authenticated:
            logger.info(f"User {request.user.username} accessing from IP: {client_ip}")

            # Check IP restrictions for this user
            try:
                employee = EmployeeRegistry.objects.get(email=request.user.email)

                if employee.ip_restriction_enabled:
                    is_allowed = employee.is_ip_allowed(client_ip)

                    logger.warning(f"IP restriction check for {employee.employee_name}: "
                                 f"Client IP {client_ip}, Allowed: {is_allowed}, "
                                 f"Allowed IPs: {employee.allowed_ip_addresses}")

                    if not is_allowed:
                        error_message = employee.ip_restriction_message or "Access restricted to authorized IP addresses only"
                        logger.error(f"IP BLOCKED: User {employee.employee_name} from IP {client_ip}")

                        return HttpResponseForbidden(f"""
                        <html>
                        <head><title>Access Denied</title></head>
                        <body>
                        <h1>🚫 Access Denied</h1>
                        <p><strong>{error_message}</strong></p>
                        <p>Your IP address: <code>{client_ip}</code></p>
                        <p>Employee: {employee.employee_name}</p>
                        <hr>
                        <small>If you believe this is an error, please contact your HR administrator.</small>
                        </body>
                        </html>
                        """)

            except EmployeeRegistry.DoesNotExist:
                logger.info(f"No EmployeeRegistry found for user {request.user.username}")

        response = self.get_response(request)
        return response