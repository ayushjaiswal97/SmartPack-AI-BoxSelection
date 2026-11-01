from django.urls import path
from . import api_views

app_name = 'catalog_api'

urlpatterns = [
    # Products REST API
    path('products/', api_views.ProductListCreateAPIView.as_view(), name='product_list_create_api'),
    path('products/<int:pk>/', api_views.ProductDetailUpdateDeleteAPIView.as_view(), name='product_detail_update_delete_api'),

    # Boxes REST API
    path('boxes/', api_views.BoxListCreateAPIView.as_view(), name='box_list_create_api'),
    path('boxes/<int:pk>/', api_views.BoxDetailUpdateDeleteAPIView.as_view(), name='box_detail_update_delete_api'),
    path('boxes/<int:pk>/toggle-active/', api_views.BoxToggleActiveAPIView.as_view(), name='box_toggle_active_api'),
]

