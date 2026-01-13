"""
API URL routing for v2 REST endpoints
"""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from . import views

app_name = 'api'

urlpatterns = [
    # Authentication endpoints
    path('auth/login/', views.login_view, name='login'),
    path('auth/login/pin/', views.pin_login_view, name='pin-login'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('auth/logout/', views.logout_view, name='logout'),
    path('auth/change-pin/', views.change_pin_view, name='change-pin'),
    path('auth/reset-pin/', views.reset_pin_view, name='reset-pin'),

    # User endpoints
    path('auth/me/', views.current_user_view, name='current-user'),

    # API Documentation (Swagger/OpenAPI)
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='api:schema'), name='docs'),
]
