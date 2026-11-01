from decimal import Decimal
from django.core.validators import MinValueValidator
from django.db import models


class Product(models.Model):
    sku = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="Unique Stock Keeping Unit identifier.",
    )
    name = models.CharField(
        max_length=255,
        help_text="Product display name.",
    )
    length = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'), message="Length must be greater than 0.")],
        help_text="Length in centimeters (cm).",
    )
    width = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'), message="Width must be greater than 0.")],
        help_text="Width in centimeters (cm).",
    )
    height = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'), message="Height must be greater than 0.")],
        help_text="Height in centimeters (cm).",
    )
    weight = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0.001'), message="Weight must be greater than 0.")],
        help_text="Weight in kilograms (kg).",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this product is currently active for ordering.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sku']
        verbose_name = 'Product'
        verbose_name_plural = 'Products'

    def __str__(self):
        return f"{self.sku} - {self.name} ({self.length}x{self.width}x{self.height} cm, {self.weight} kg)"

    @property
    def volume(self) -> Decimal:
        """Returns product volume in cubic centimeters (cm³)."""
        return self.length * self.width * self.height


class ShippingBox(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Box name/code (e.g. Small Box, Medium Standard, Large Heavy).",
    )
    internal_length = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'), message="Internal length must be greater than 0.")],
        help_text="Internal length in centimeters (cm).",
    )
    internal_width = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'), message="Internal width must be greater than 0.")],
        help_text="Internal width in centimeters (cm).",
    )
    internal_height = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'), message="Internal height must be greater than 0.")],
        help_text="Internal height in centimeters (cm).",
    )
    max_weight_capacity = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0.001'), message="Max weight capacity must be greater than 0.")],
        help_text="Maximum weight capacity in kilograms (kg).",
    )
    packaging_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'), message="Packaging cost cannot be negative.")],
        help_text="Packaging cost in currency units (e.g. $).",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this box is available for packing recommendations.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['packaging_cost', 'name']
        verbose_name = 'Shipping Box'
        verbose_name_plural = 'Shipping Boxes'

    def __str__(self):
        return (
            f"{self.name} ({self.internal_length}x{self.internal_width}x{self.internal_height} cm, "
            f"Max {self.max_weight_capacity} kg, Cost ${self.packaging_cost})"
        )

    @property
    def internal_volume(self) -> Decimal:
        """Returns internal usable box volume in cubic centimeters (cm³)."""
        return self.internal_length * self.internal_width * self.internal_height
