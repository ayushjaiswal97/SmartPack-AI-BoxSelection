from django.contrib import admin
from .models import Order, OrderItem, PackingResult


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = (
        'product',
        'quantity',
        'unit_length_snapshot',
        'unit_width_snapshot',
        'unit_height_snapshot',
        'unit_weight_snapshot',
        'created_at',
    )
    readonly_fields = (
        'unit_length_snapshot',
        'unit_width_snapshot',
        'unit_height_snapshot',
        'unit_weight_snapshot',
        'created_at',
    )


class PackingResultInline(admin.StackedInline):
    model = PackingResult
    can_delete = False
    readonly_fields = (
        'is_feasible',
        'failure_reason',
        'volume_utilization_pct',
        'weight_utilization_pct',
        'execution_time_ms',
        'evaluated_at',
    )


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'order_number',
        'customer_reference',
        'status',
        'selected_box',
        'total_weight',
        'total_volume',
        'packaging_cost',
        'created_at',
    )
    list_filter = ('status', 'selected_box', 'created_at')
    search_fields = ('order_number', 'customer_reference', 'notes')
    inlines = [OrderItemInline, PackingResultInline]


@admin.register(PackingResult)
class PackingResultAdmin(admin.ModelAdmin):
    list_display = (
        'order',
        'is_feasible',
        'volume_utilization_pct',
        'weight_utilization_pct',
        'execution_time_ms',
        'evaluated_at',
    )
    list_filter = ('is_feasible',)
