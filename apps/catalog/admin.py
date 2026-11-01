from django.contrib import admin
from .models import Product, ShippingBox


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('sku', 'name', 'length', 'width', 'height', 'weight', 'is_active', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('sku', 'name')
    ordering = ('sku',)


@admin.register(ShippingBox)
class ShippingBoxAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'internal_length',
        'internal_width',
        'internal_height',
        'max_weight_capacity',
        'packaging_cost',
        'is_active',
        'updated_at',
    )
    list_filter = ('is_active',)
    search_fields = ('name',)
    ordering = ('packaging_cost', 'name')
