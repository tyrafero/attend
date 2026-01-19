"""
API URL routing for v2 REST endpoints
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from . import views
from . import attendance_views
from . import report_views

app_name = 'api'

# Create router for ViewSets
router = DefaultRouter()
router.register(r'departments', attendance_views.DepartmentViewSet, basename='department')
router.register(r'shifts', attendance_views.ShiftViewSet, basename='shift')
router.register(r'employees', attendance_views.EmployeeProfileViewSet, basename='employee')
router.register(r'attendance/daily-summary', attendance_views.DailySummaryViewSet, basename='daily-summary')
router.register(r'attendance/taps', attendance_views.AttendanceTapViewSet, basename='attendance-tap')
router.register(r'shift-assignments', attendance_views.ShiftAssignmentViewSet, basename='shift-assignment')
router.register(r'til/records', attendance_views.TILRecordViewSet, basename='til-record')
router.register(r'leaves', attendance_views.LeaveRecordViewSet, basename='leave')

urlpatterns = [
    # Authentication endpoints
    path('auth/login/', views.login_view, name='login'),
    path('auth/login/pin/', views.pin_login_view, name='pin-login'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('auth/logout/', views.logout_view, name='logout'),
    path('auth/change-pin/', views.change_pin_view, name='change-pin'),
    path('auth/change-password/', views.change_password_view, name='change-password'),
    path('auth/reset-pin/', views.reset_pin_view, name='reset-pin'),

    # User endpoints
    path('auth/me/', views.current_user_view, name='current-user'),

    # Attendance endpoints
    path('attendance/clock/', attendance_views.clock_action_view, name='clock-action'),
    path('attendance/me/current/', attendance_views.current_status_view, name='current-status'),
    path('attendance/me/summary/', attendance_views.my_attendance_summary_view, name='my-summary'),

    # TIL endpoints
    path('til/balance/', attendance_views.my_til_balance_view, name='my-til-balance'),

    # Early Birds (for managers)
    path('attendance/early-birds/', attendance_views.early_birds_view, name='early-birds'),

    # Reports endpoints
    path('reports/attendance/', report_views.attendance_report_view, name='attendance-report'),
    path('reports/attendance/export/', report_views.attendance_export_view, name='attendance-export'),
    path('reports/til/', report_views.til_report_view, name='til-report'),
    path('reports/til/export/', report_views.til_export_view, name='til-export'),
    path('reports/leaves/', report_views.leave_report_view, name='leave-report'),
    path('reports/leaves/export/', report_views.leave_export_view, name='leave-export'),
    path('reports/team/', report_views.team_report_view, name='team-report'),
    path('reports/analytics/attendance-trends/', report_views.attendance_trends_view, name='attendance-trends'),
    path('reports/analytics/department-comparison/', report_views.department_comparison_view, name='department-comparison'),

    # Include router URLs
    path('', include(router.urls)),

    # API Documentation (Swagger/OpenAPI)
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='api:schema'), name='docs'),
]
