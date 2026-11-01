from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('', views.OrderSimulatorView.as_view(), name='simulator'),
    path('recommendation/<str:order_number>/', views.OrderRecommendationView.as_view(), name='recommendation'),
    path('history/', views.OrderListView.as_view(), name='order_list'),
    path('history/<str:order_number>/', views.OrderDetailView.as_view(), name='order_detail'),
]

