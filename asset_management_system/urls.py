"""
URL configuration for asset_management_system project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
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
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from assets import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.landing_page, name='index'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('assets/', views.asset_list, name='asset_list'),
    path('assets/<int:pk>/', views.asset_detail, name='asset_detail'),
    path('assets/create/', views.asset_create, name='asset_create'),
    path('assets/<int:pk>/edit/', views.asset_update, name='asset_update'),
    path('assets/<int:pk>/delete/', views.asset_delete, name='asset_delete'),
    path('assets/<int:pk>/request/', views.request_asset, name='request_asset'),
    path('requests/', views.manage_requests, name='manage_requests'),
    path('requests/<int:request_id>/<str:action>/', views.process_request, name='process_request'),
    path('switch-user/', views.switch_user, name='switch_user'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('reports/', views.reports, name='reports'),
    path('reports/download/', views.download_report, name='download_report'),
    path('requests/clear-history/', views.clear_request_history, name='clear_request_history'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
