from django.urls import path
from . import api_views, views

app_name = 'orders'

urlpatterns = [
    # UI Views
    path('', views.OrderSimulatorView.as_view(), name='simulator'),
    path('recommendation/<str:order_number>/', views.OrderRecommendationView.as_view(), name='recommendation'),
    path('history/', views.OrderListView.as_view(), name='order_list'),
    path('history/<str:order_number>/', views.OrderDetailView.as_view(), name='order_detail'),

    # Packaging Engine API Endpoints
    path('api/orders/<str:order_id>/recommend-box/', api_views.RecommendBoxAPIView.as_view(), name='api_recommend_box'),
]
