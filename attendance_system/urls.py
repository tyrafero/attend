"""
URL configuration for attendance_system project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.contrib.admin.views.decorators import staff_member_required
from attendance import views as attendance_views

urlpatterns = [
    path('django-admin/', admin.site.urls),  # Renamed to avoid conflict
    path('django-admin/reports/', staff_member_required(attendance_views.reports_view), name='admin_reports'),
    path('django-admin/reports/export/csv/', staff_member_required(attendance_views.export_csv), name='admin_export_csv'),
    path('django-admin/reports/export/pdf/', staff_member_required(attendance_views.export_pdf), name='admin_export_pdf'),
    path('', include('attendance.urls')),  # Attendance app URLs
]
