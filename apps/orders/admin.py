from django.contrib import admin, messages
from django.utils.html import format_html
from .models import Order, OrderItem, PackingResult
from .services import PackagingService


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1
    autocomplete_fields = ['product']
    fields = (
        'product',
        'quantity',
        'display_subtotal_weight',
        'display_subtotal_volume',
        'unit_length_snapshot',
        'unit_width_snapshot',
        'unit_height_snapshot',
        'unit_weight_snapshot',
    )
    readonly_fields = (
        'display_subtotal_weight',
        'display_subtotal_volume',
        'unit_length_snapshot',
        'unit_width_snapshot',
        'unit_height_snapshot',
        'unit_weight_snapshot',
    )

    @admin.display(description="Subtotal Wt")
    def display_subtotal_weight(self, obj: OrderItem) -> str:
        if obj.pk:
            return f"{obj.total_weight:.3f} kg"
        return "—"

    @admin.display(description="Subtotal Vol")
    def display_subtotal_volume(self, obj: OrderItem) -> str:
        if obj.pk:
            return f"{obj.total_volume:,.1f} cm³"
        return "—"


class PackingResultInline(admin.StackedInline):
    model = PackingResult
    can_delete = False
    fields = (
        'is_feasible',
        'failure_reason',
        ('volume_utilization_pct', 'weight_utilization_pct'),
        'execution_time_ms',
        'evaluated_at',
    )
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
        'display_status_badge',
        'selected_box',
        'display_total_weight',
        'display_total_volume',
        'display_packaging_cost',
        'created_at',
    )
    list_filter = ('status', 'selected_box', 'created_at')
    search_fields = ('order_number', 'customer_reference', 'notes')
    ordering = ('-created_at',)
    readonly_fields = (
        'total_weight',
        'total_volume',
        'packaging_cost',
        'created_at',
        'updated_at',
    )
    autocomplete_fields = ['selected_box']
    inlines = [OrderItemInline, PackingResultInline]
    actions = ['evaluate_box_selection', 'mark_as_packed']

    fieldsets = (
        ('Order Identification', {
            'fields': (
                ('order_number', 'customer_reference'),
                'status',
            )
        }),
        ('Packaging Recommendation & Metrics', {
            'fields': (
                'selected_box',
                'packaging_cost',
                ('total_weight', 'total_volume'),
            ),
            'description': 'Computed automatically by the 3D Extreme Points packaging optimization engine.',
        }),
        ('Warehouse Packaging Instructions', {
            'fields': ('notes',),
        }),
        ('Audit Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description="Status")
    def display_status_badge(self, obj: Order) -> str:
        colors = {
            Order.Status.EVALUATED: ("#10b981", "#ffffff"),  # Green
            Order.Status.PACKED: ("#2563eb", "#ffffff"),     # Blue
            Order.Status.FAILED: ("#ef4444", "#ffffff"),     # Red
            Order.Status.DRAFT: ("#64748b", "#ffffff"),      # Gray
        }
        bg, fg = colors.get(obj.status, ("#64748b", "#ffffff"))
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 3px 8px; border-radius: 4px; font-weight: 600; font-size: 0.8rem;">{}</span>',
            bg,
            fg,
            obj.get_status_display(),
        )

    @admin.display(description="Order Weight")
    def display_total_weight(self, obj: Order) -> str:
        return f"{obj.total_weight:.3f} kg"

    @admin.display(description="Item Volume")
    def display_total_volume(self, obj: Order) -> str:
        return f"{obj.total_volume:,.1f} cm³"

    @admin.display(description="Packaging Cost")
    def display_packaging_cost(self, obj: Order) -> str:
        if obj.packaging_cost is not None:
            return f"₹{obj.packaging_cost:.2f}"
        return "—"

    @admin.action(description="Run 3D Box Selection for selected orders")
    def evaluate_box_selection(self, request, queryset):
        success_count = 0
        infeasible_count = 0
        error_count = 0

        for order in queryset:
            try:
                res = PackagingService.recommend_box_for_order(order.id)
                if res.get("selection_status") == "FEASIBLE":
                    success_count += 1
                else:
                    infeasible_count += 1
            except Exception as e:
                error_count += 1

        self.message_user(
            request,
            f"Evaluated {queryset.count()} order(s): {success_count} box assigned, "
            f"{infeasible_count} infeasible, {error_count} errors.",
            level=messages.SUCCESS if error_count == 0 else messages.WARNING,
        )

    @admin.action(description="Mark selected orders as Packed & Dispatched")
    def mark_as_packed(self, request, queryset):
        updated = queryset.update(status=Order.Status.PACKED)
        self.message_user(request, f"{updated} order(s) marked as Packed & Dispatched.")

    def save_related(self, request, form, formsets, change):
        """
        When inline order items are saved or modified in the Django admin,
        automatically trigger box selection so the recommendation and
        placed item manifest stay synchronized with inventory changes.
        """
        super().save_related(request, form, formsets, change)
        order = form.instance
        if order.items.exists():
            try:
                PackagingService.recommend_box_for_order(order.id)
            except Exception:
                pass


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'order',
        'product',
        'quantity',
        'display_total_weight',
        'display_total_volume',
        'created_at',
    )
    list_filter = ('created_at',)
    search_fields = ('order__order_number', 'product__sku', 'product__name')
    autocomplete_fields = ['order', 'product']
    ordering = ('-id',)
    readonly_fields = (
        'created_at',
        'unit_length_snapshot',
        'unit_width_snapshot',
        'unit_height_snapshot',
        'unit_weight_snapshot',
    )

    @admin.display(description="Total Weight")
    def display_total_weight(self, obj: OrderItem) -> str:
        return f"{obj.total_weight:.3f} kg"

    @admin.display(description="Total Volume")
    def display_total_volume(self, obj: OrderItem) -> str:
        return f"{obj.total_volume:,.1f} cm³"


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
    list_filter = ('is_feasible', 'evaluated_at')
    search_fields = ('order__order_number',)
    readonly_fields = (
        'order',
        'is_feasible',
        'failure_reason',
        'volume_utilization_pct',
        'weight_utilization_pct',
        'placed_items_manifest',
        'execution_time_ms',
        'evaluated_at',
    )
