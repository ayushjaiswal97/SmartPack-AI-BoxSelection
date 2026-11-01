from django.urls import path
from . import api_views, views

app_name = 'orders'

urlpatterns = [
    # Dashboard & Primary Navigation
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('simulator/', views.OrderSimulatorView.as_view(), name='simulator'),
    path('orders/', views.OrderListView.as_view(), name='order_list'),
    path('history/', views.RecommendationHistoryView.as_view(), name='history_list'),
    path('recommendation/<str:order_number>/', views.OrderRecommendationView.as_view(), name='recommendation'),
    path('orders/<str:order_number>/', views.OrderDetailView.as_view(), name='order_detail'),

    # Packaging Engine & Order API Endpoints
    path('api/orders/', api_views.OrderListCreateAPIView.as_view(), name='api_order_list_create'),
    path('api/orders/<str:order_id>/', api_views.OrderDetailAPIView.as_view(), name='api_order_detail'),
    path('api/orders/<str:order_id>/recommend-box/', api_views.RecommendBoxAPIView.as_view(), name='api_recommend_box'),
]
