import uuid
from decimal import Decimal
from django.core.validators import MinValueValidator
from django.db import models
from apps.catalog.models import Box, Product


class Order(models.Model):
    """
    Represents a fulfillment order consisting of one or more line items.
    """
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        EVALUATED = "EVALUATED", "Evaluated / Box Assigned"
        PACKED = "PACKED", "Packed & Dispatched"
        FAILED = "FAILED", "Packing Infeasible"

    order_number = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="Unique warehouse order identifier (e.g. ORD-20261101-ABCD).",
    )
    customer_reference = models.CharField(
        max_length=128,
        blank=True,
        default="",
        help_text="Customer name, account code, or external ERP reference.",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
        help_text="Current fulfillment lifecycle status.",
    )
    selected_box = models.ForeignKey(
        Box,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="orders",
        help_text="Assigned lowest-cost feasible box determined by the packing service.",
    )
    total_weight = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        default=Decimal("0.000"),
        help_text="Calculated total order weight in kg.",
    )
    total_volume = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Calculated total item volume in cm³.",
    )
    packaging_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Packaging cost of the selected box.",
    )
    notes = models.TextField(
        blank=True,
        help_text="Optional internal warehouse packaging instructions or notes.",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="Timestamp when the order was created.",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when the order status or assignment was updated.",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Order"
        verbose_name_plural = "Orders"
        indexes = [
            models.Index(fields=["order_number"], name="idx_order_number"),
            models.Index(fields=["status", "created_at"], name="idx_order_status_created"),
        ]

    def __str__(self) -> str:
        ref = f" ({self.customer_reference})" if self.customer_reference else ""
        return f"Order #{self.order_number}{ref} [{self.get_status_display()}]"

    @classmethod
    def generate_order_number(cls) -> str:
        """Generates a unique short order reference."""
        return f"ORD-{uuid.uuid4().hex[:8].upper()}"

    @property
    def total_order_weight(self) -> Decimal:
        """Alias for total_weight."""
        return self.total_weight


class OrderItem(models.Model):
    """
    Represents a discrete line item in an Order mapping a Product to a Quantity.
    """
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
        help_text="The parent order containing this item.",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="order_items",
        help_text="The product SKU to be packed.",
    )
    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text="Number of units of this product. Must be >= 1.",
    )
    # Snapshots to preserve historical accuracy if product dimensions change in catalog later
    unit_length_snapshot = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Length snapshot at order time in cm.",
    )
    unit_width_snapshot = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Width snapshot at order time in cm.",
    )
    unit_height_snapshot = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Height snapshot at order time in cm.",
    )
    unit_weight_snapshot = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Weight snapshot at order time in kg.",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when this item was added to the order.",
    )

    class Meta:
        ordering = ["id"]
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"
        indexes = [
            models.Index(fields=["order", "product"], name="idx_orderitem_order_prod"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gt=0),
                name="chk_orderitem_quantity_positive",
            ),
            models.UniqueConstraint(
                fields=["order", "product"],
                name="uniq_product_per_order",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.quantity}x {self.product.sku} on Order #{self.order.order_number}"

    def save(self, *args, **kwargs):
        if self.product_id:
            if not self.unit_length_snapshot:
                self.unit_length_snapshot = self.product.length
            if not self.unit_width_snapshot:
                self.unit_width_snapshot = self.product.width
            if not self.unit_height_snapshot:
                self.unit_height_snapshot = self.product.height
            if not self.unit_weight_snapshot:
                self.unit_weight_snapshot = self.product.weight
        super().save(*args, **kwargs)

    @property
    def total_weight(self) -> Decimal:
        unit_wt = self.unit_weight_snapshot or self.product.weight
        return unit_wt * self.quantity

    @property
    def total_volume(self) -> Decimal:
        l = self.unit_length_snapshot or self.product.length
        w = self.unit_width_snapshot or self.product.width
        h = self.unit_height_snapshot or self.product.height
        return l * w * h * self.quantity


class PackingResult(models.Model):
    """
    Persists evaluation outcomes, space utilization, and 3D spatial placements
    for an order without coupling algorithm logic to the domain model.
    """
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name="packing_result",
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
        default=Decimal("0.00"),
        help_text="Volume space utilization percentage (0 - 100%).",
    )
    weight_utilization_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Weight capacity utilization percentage (0 - 100%).",
    )
    placed_items_manifest = models.JSONField(
        default=list,
        blank=True,
        help_text="JSON list of 3D item placements [{sku, x, y, z, dx, dy, dz}].",
    )
    execution_time_ms = models.IntegerField(
        default=0,
        help_text="Algorithm computation runtime in milliseconds.",
    )
    evaluated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        status = "Feasible" if self.is_feasible else "Infeasible"
        return f"PackingResult for Order #{self.order.order_number}: {status}"
