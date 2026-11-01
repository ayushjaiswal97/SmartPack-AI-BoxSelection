from decimal import Decimal
import pytest
from django.db import IntegrityError
from apps.catalog.models import Box, Product
from apps.orders.models import Order, OrderItem


@pytest.mark.django_db
def test_product_dimensions_must_be_positive():
    """Verify that DB-level CheckConstraint rejects zero or negative dimension."""
    with pytest.raises(IntegrityError):
        Product.objects.create(
            sku="INV-LEN-0",
            name="Invalid Length",
            length=Decimal("0.00"),  # Violates chk_product_length_positive
            width=Decimal("10.00"),
            height=Decimal("10.00"),
            weight=Decimal("1.000"),
        )


@pytest.mark.django_db
def test_product_weight_must_be_positive():
    """Verify that DB-level CheckConstraint rejects zero or negative weight."""
    with pytest.raises(IntegrityError):
        Product.objects.create(
            sku="INV-WT-0",
            name="Invalid Weight",
            length=Decimal("10.00"),
            width=Decimal("10.00"),
            height=Decimal("10.00"),
            weight=Decimal("0.000"),  # Violates chk_product_weight_positive
        )


@pytest.mark.django_db
def test_box_packaging_cost_must_be_non_negative():
    """Verify that DB-level CheckConstraint rejects negative packaging cost."""
    with pytest.raises(IntegrityError):
        Box.objects.create(
            name="Negative Cost Box",
            internal_length=Decimal("10.00"),
            internal_width=Decimal("10.00"),
            internal_height=Decimal("10.00"),
            max_weight_capacity=Decimal("5.000"),
            packaging_cost=Decimal("-1.00"),  # Violates chk_box_cost_non_negative
        )


@pytest.mark.django_db
def test_orderitem_quantity_must_be_positive():
    """Verify that DB-level CheckConstraint rejects zero quantity."""
    prod = Product.objects.create(
        sku="TEST-QTY",
        name="Test Item",
        length=Decimal("10.00"),
        width=Decimal("10.00"),
        height=Decimal("10.00"),
        weight=Decimal("1.000"),
    )
    order = Order.objects.create(order_number="ORD-QTY-TEST")
    with pytest.raises(IntegrityError):
        OrderItem.objects.create(
            order=order,
            product=prod,
            quantity=0,  # Violates chk_orderitem_quantity_positive
        )


@pytest.mark.django_db
def test_orderitem_unique_product_per_order():
    """Verify that DB-level UniqueConstraint prevents adding duplicate SKU rows."""
    prod = Product.objects.create(
        sku="TEST-UNIQ",
        name="Test Item",
        length=Decimal("10.00"),
        width=Decimal("10.00"),
        height=Decimal("10.00"),
        weight=Decimal("1.000"),
    )
    order = Order.objects.create(order_number="ORD-UNIQ-TEST")
    OrderItem.objects.create(order=order, product=prod, quantity=1)

    with pytest.raises(IntegrityError):
        # Adding same product to same order again must violate uniq_product_per_order
        OrderItem.objects.create(order=order, product=prod, quantity=2)

