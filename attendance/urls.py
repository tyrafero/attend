from django.urls import path
from . import views

app_name = 'attendance'

urlpatterns = [
    # Employee screens
    path('', views.welcome_screen, name='welcome'),
    path('clock/', views.clock_action, name='clock_action'),

    # Admin screens
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/employees/add/', views.add_employee, name='add_employee'),
]
