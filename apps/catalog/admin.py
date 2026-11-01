from django.contrib import admin
from .models import Box, Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('sku', 'name', 'length', 'width', 'height', 'weight', 'created_at', 'updated_at')
    search_fields = ('sku', 'name')
    ordering = ('sku',)


@admin.register(Box)
class BoxAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'internal_length',
        'internal_width',
        'internal_height',
        'max_weight_capacity',
        'packaging_cost',
        'is_active',
        'created_at',
        'updated_at',
    )
    list_filter = ('is_active',)
    search_fields = ('name',)
    ordering = ('packaging_cost', 'name')
