from decimal import Decimal
from django.core.validators import MinValueValidator
from django.db import models


class Product(models.Model):
    """
    Represents a discrete catalog item with physical bounding specifications.
    
    Dimensions are measured in centimeters (cm) and weight in kilograms (kg).
    """
    sku = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="Unique Stock Keeping Unit identifier (e.g. ELEC-PHN-01).",
    )
    name = models.CharField(
        max_length=255,
        help_text="Product commercial name.",
    )
    length = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Length along the X-axis in centimeters (cm). Must be > 0.",
    )
    width = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Width along the Y-axis in centimeters (cm). Must be > 0.",
    )
    height = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Height along the Z-axis in centimeters (cm). Must be > 0.",
    )
    weight = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0.001'))],
        help_text="Physical unit weight in kilograms (kg). Must be > 0.",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the product was registered.",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when the product details were last updated.",
    )

    class Meta:
        ordering = ["sku"]
        verbose_name = "Product"
        verbose_name_plural = "Products"
        indexes = [
            models.Index(fields=["sku"], name="idx_product_sku"),
            models.Index(fields=["name"], name="idx_product_name"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(length__gt=Decimal('0.00')),
                name="chk_product_length_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(width__gt=Decimal('0.00')),
                name="chk_product_width_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(height__gt=Decimal('0.00')),
                name="chk_product_height_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(weight__gt=Decimal('0.000')),
                name="chk_product_weight_positive",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.sku} - {self.name} ({self.length}x{self.width}x{self.height} cm, {self.weight} kg)"

    @property
    def volume(self) -> Decimal:
        """Returns bounding volume in cubic centimeters (cm³)."""
        return self.length * self.width * self.height


class Box(models.Model):
    """
    Represents a standardized shipping container used in the warehouse.
    
    All dimensions denote internal usable clearance in centimeters (cm).
    """
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Descriptive shipping container code (e.g. Standard Medium Box, BX-MD).",
    )
    internal_length = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Internal clearance length in centimeters (cm). Must be > 0.",
    )
    internal_width = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Internal clearance width in centimeters (cm). Must be > 0.",
    )
    internal_height = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Internal clearance height in centimeters (cm). Must be > 0.",
    )
    max_weight_capacity = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0.001'))],
        help_text="Maximum gross payload capacity in kilograms (kg). Must be > 0.",
    )
    packaging_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Procurement or unit cost of the packaging material (₹). Must be >= 0.",
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Controls whether this box is considered during packing optimization.",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the box specification was added.",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when the box specification was last modified.",
    )

    class Meta:
        ordering = ["packaging_cost", "name"]
        verbose_name = "Shipping Box"
        verbose_name_plural = "Shipping Boxes"
        indexes = [
            models.Index(
                fields=["is_active", "packaging_cost"],
                name="idx_box_active_cost",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(internal_length__gt=Decimal('0.00')),
                name="chk_box_length_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(internal_width__gt=Decimal('0.00')),
                name="chk_box_width_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(internal_height__gt=Decimal('0.00')),
                name="chk_box_height_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(max_weight_capacity__gt=Decimal('0.000')),
                name="chk_box_max_weight_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(packaging_cost__gte=Decimal('0.00')),
                name="chk_box_cost_non_negative",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.name} ({self.internal_length}x{self.internal_width}x{self.internal_height} cm, "
            f"Cap: {self.max_weight_capacity} kg, Cost: ₹{self.packaging_cost})"
        )

    @property
    def internal_volume(self) -> Decimal:
        """Returns usable volume in cubic centimeters (cm³)."""
        return self.internal_length * self.internal_width * self.internal_height

    @property
    def volume(self) -> Decimal:
        """Alias for internal_volume."""
        return self.internal_volume
