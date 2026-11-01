from django.contrib import admin
from django.utils.html import format_html
from .models import Box, Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'sku',
        'name',
        'display_dimensions',
        'display_volume',
        'display_weight',
        'created_at',
    )
    search_fields = ('sku', 'name')
    ordering = ('sku',)
    readonly_fields = ('created_at', 'updated_at', 'display_volume')
    fieldsets = (
        ('Product Identification', {
            'fields': ('sku', 'name')
        }),
        ('Physical Clearance Dimensions (cm)', {
            'fields': (
                ('length', 'width', 'height'),
                'display_volume',
            ),
            'description': 'Bounding dimensions along orthogonal axes used by the 3D packing engine.',
        }),
        ('Weight Specification (kg)', {
            'fields': ('weight',),
            'description': 'Individual unit weight in kilograms.',
        }),
        ('Audit Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description="Dimensions (L × W × H)")
    def display_dimensions(self, obj: Product) -> str:
        return f"{obj.length} × {obj.width} × {obj.height} cm"

    @admin.display(description="Unit Volume")
    def display_volume(self, obj: Product) -> str:
        vol = obj.volume
        return f"{vol:,.1f} cm³"

    @admin.display(description="Unit Weight")
    def display_weight(self, obj: Product) -> str:
        return f"{obj.weight:.3f} kg"


@admin.register(Box)
class BoxAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'display_clearance',
        'display_volume',
        'display_capacity',
        'display_cost',
        'is_active',
        'updated_at',
    )
    list_filter = ('is_active',)
    search_fields = ('name',)
    ordering = ('packaging_cost', 'name')
    readonly_fields = ('created_at', 'updated_at', 'display_volume')
    actions = ['activate_boxes', 'deactivate_boxes']

    fieldsets = (
        ('Box Specification', {
            'fields': ('name', 'is_active')
        }),
        ('Internal Clearances (cm)', {
            'fields': (
                ('internal_length', 'internal_width', 'internal_height'),
                'display_volume',
            ),
            'description': 'Usable internal cavity dimensions for item placement.',
        }),
        ('Payload & Financial Specifications', {
            'fields': (
                ('max_weight_capacity', 'packaging_cost'),
            ),
        }),
        ('Audit Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description="Internal Clearance (L × W × H)")
    def display_clearance(self, obj: Box) -> str:
        return f"{obj.internal_length} × {obj.internal_width} × {obj.internal_height} cm"

    @admin.display(description="Cavity Volume")
    def display_volume(self, obj: Box) -> str:
        vol = obj.internal_volume
        return f"{vol:,.1f} cm³"

    @admin.display(description="Max Weight Payload")
    def display_capacity(self, obj: Box) -> str:
        return f"{obj.max_weight_capacity:.3f} kg"

    @admin.display(description="Unit Packaging Cost")
    def display_cost(self, obj: Box) -> str:
        return f"${obj.packaging_cost:.2f}"

    @admin.action(description="Mark selected boxes as Active for packing engine")
    def activate_boxes(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} shipping box(es) marked as active.")

    @admin.action(description="Mark selected boxes as Inactive (disable recommendation)")
    def deactivate_boxes(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} shipping box(es) marked as inactive.")
