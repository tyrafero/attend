"""
URL configuration for attendance_system project.
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.contrib.admin.views.decorators import staff_member_required
from django.views.generic import TemplateView
from django.conf import settings
from django.http import HttpResponse
import os
from attendance import views as attendance_views


def serve_react_app(request):
    """Serve the React app's index.html"""
    # Try multiple possible locations
    possible_paths = [
        os.path.join(settings.BASE_DIR, 'staticfiles', 'frontend', 'index.html'),
        os.path.join(settings.BASE_DIR, 'frontend', 'dist', 'index.html'),
    ]

    for index_path in possible_paths:
        if os.path.exists(index_path):
            with open(index_path, 'r') as f:
                return HttpResponse(f.read(), content_type='text/html')

    return HttpResponse('React app not built. Run: cd frontend && npm run build', status=404)


# React frontend routes - these will be served by the React app
REACT_ROUTES = [
    'login',
    'dashboard',
    'shifts',
    'til',
    'leave',
    'reports',
    'admin',
    'team',
]

urlpatterns = [
    path('django-admin/', admin.site.urls),  # Django admin
    path('django-admin/reports/', staff_member_required(attendance_views.reports_view), name='admin_reports'),
    path('django-admin/reports/export/csv/', staff_member_required(attendance_views.export_csv), name='admin_export_csv'),
    path('django-admin/reports/export/pdf/', staff_member_required(attendance_views.export_pdf), name='admin_export_pdf'),

    # V2 REST API endpoints
    path('api/', include('attendance.api.urls')),

    # V1 kiosk/attendance routes (keep for backwards compatibility)
    path('v1/', include('attendance.urls')),

    # Serve React app for frontend routes
    path('', serve_react_app, name='react-home'),
]

# Add all React routes
for route in REACT_ROUTES:
    urlpatterns.append(path(f'{route}/', serve_react_app, name=f'react-{route}'))
    urlpatterns.append(path(f'{route}', serve_react_app))
