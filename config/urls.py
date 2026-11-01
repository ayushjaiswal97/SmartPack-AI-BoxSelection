from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    # Authentication
    path('accounts/login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    # Apps
    path('api/', include('apps.catalog.api_urls', namespace='catalog_api')),
    path('catalog/', include('apps.catalog.urls', namespace='catalog')),
    path('', include('apps.orders.urls', namespace='orders')),
]
