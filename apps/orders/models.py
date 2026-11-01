import uuid
from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from apps.catalog.models import Product, ShippingBox


class Order(models.Model):
    STATUS_DRAFT = 'DRAFT'
    STATUS_EVALUATED = 'EVALUATED'
    STATUS_PACKED = 'PACKED'
    STATUS_FAILED = 'FAILED'

    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_EVALUATED, 'Evaluated / Ready to Pack'),
        (STATUS_PACKED, 'Packed & Dispatched'),
        (STATUS_FAILED, 'Packing Infeasible'),
    ]

    order_number = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="Unique order reference identifier.",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
    )
    selected_box = models.ForeignKey(
        ShippingBox,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='orders',
        help_text="The recommended lowest-cost feasible box.",
    )
    total_weight = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        default=Decimal('0.000'),
        help_text="Calculated total order weight in kg.",
    )
    total_volume = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Calculated total item volume in cm³.",
    )
    packaging_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Packaging cost of the selected box.",
    )
    notes = models.TextField(blank=True, help_text="Optional order notes or customer instructions.")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_orders',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.order_number} ({self.status})"

    @classmethod
    def generate_order_number(cls) -> str:
        """Generates a unique short order reference."""
        return f"ORD-{uuid.uuid4().hex[:8].upper()}"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='order_items',
    )
    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1, message="Quantity must be at least 1.")],
    )
    # Snapshots to preserve historical accuracy if product dimensions change later
    unit_length_snapshot = models.DecimalField(max_digits=8, decimal_places=2)
    unit_width_snapshot = models.DecimalField(max_digits=8, decimal_places=2)
    unit_height_snapshot = models.DecimalField(max_digits=8, decimal_places=2)
    unit_weight_snapshot = models.DecimalField(max_digits=8, decimal_places=3)

    class Meta:
        ordering = ['id']
        constraints = [
            models.UniqueConstraint(fields=['order', 'product'], name='unique_product_per_order')
        ]

    def __str__(self):
        return f"{self.quantity}x {self.product.sku} ({self.product.name})"

    def save(self, *args, **kwargs):
        # Automatically snapshot product physical specs if not already populated
        if not self.unit_length_snapshot and self.product_id:
            self.unit_length_snapshot = self.product.length
            self.unit_width_snapshot = self.product.width
            self.unit_height_snapshot = self.product.height
            self.unit_weight_snapshot = self.product.weight
        super().save(*args, **kwargs)

    @property
    def total_weight(self) -> Decimal:
        return (self.unit_weight_snapshot or self.product.weight) * self.quantity

    @property
    def total_volume(self) -> Decimal:
        unit_vol = (
            (self.unit_length_snapshot or self.product.length)
            * (self.unit_width_snapshot or self.product.width)
            * (self.unit_height_snapshot or self.product.height)
        )
        return unit_vol * self.quantity


class PackingResult(models.Model):
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name='packing_result',
    )
    is_feasible = models.BooleanField(
        default=False,
        help_text="Indicates if a valid box was found that can pack all items.",
    )
    failure_reason = models.TextField(
        blank=True,
        help_text="Detailed failure explanation if no box could fit the order.",
    )
    volume_utilization_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Volume space utilization percentage (0 - 100%).",
    )
    weight_utilization_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Weight capacity utilization percentage (0 - 100%).",
    )
    placed_items_manifest = models.JSONField(
        default=list,
        blank=True,
        help_text="JSON list of 3D item placements [{sku, x, y, z, dx, dy, dz, rotation}].",
    )
    execution_time_ms = models.IntegerField(
        default=0,
        help_text="Algorithm computation runtime in milliseconds.",
    )
    evaluated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        status = "Feasible" if self.is_feasible else "Infeasible"
        return f"PackingResult for Order #{self.order.order_number}: {status}"
