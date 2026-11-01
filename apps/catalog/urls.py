from django.urls import path
from . import views

app_name = 'catalog'

urlpatterns = [
    path('products/', views.ProductListView.as_view(), name='product_list'),
    path('products/add/', views.ProductCreateView.as_view(), name='product_create'),
    path('products/<int:pk>/edit/', views.ProductUpdateView.as_view(), name='product_edit'),
    path('boxes/', views.ShippingBoxListView.as_view(), name='box_list'),
    path('boxes/add/', views.ShippingBoxCreateView.as_view(), name='box_create'),
    path('boxes/<int:pk>/edit/', views.ShippingBoxUpdateView.as_view(), name='box_edit'),
]

