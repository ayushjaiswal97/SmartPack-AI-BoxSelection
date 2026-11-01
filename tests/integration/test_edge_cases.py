from decimal import Decimal
import pytest
from apps.catalog.models import Box, Product
from apps.orders.models import Order, OrderItem
from apps.orders.services import evaluate_and_pack_order


@pytest.mark.django_db
def test_edge_case_empty_box_catalog():
    """When no active boxes exist, system must return a clean, actionable error."""
    Box.objects.all().delete()
    prod = Product.objects.create(
        sku="ITEM-01",
        name="Small Item",
        length=Decimal("10"),
        width=Decimal("10"),
        height=Decimal("10"),
        weight=Decimal("1"),
    )
    order = Order.objects.create(order_number="ORD-NO-BOXES")
    OrderItem.objects.create(order=order, product=prod, quantity=1)

    order, result, _ = evaluate_and_pack_order(order)
    assert order.status == Order.Status.FAILED
    assert "No active shipping boxes" in result.failure_reason


@pytest.mark.django_db
def test_edge_case_dense_overweight_order():
    """Dense small products (like dumbbells) that fit volumetrically but exceed weight capacity."""
    Box.objects.create(
        name="Standard Box",
        internal_length=Decimal("50.00"),
        internal_width=Decimal("50.00"),
        internal_height=Decimal("50.00"),
        max_weight_capacity=Decimal("10.000"),
        packaging_cost=Decimal("3.50"),
    )
    dumbbell = Product.objects.create(
        sku="DUMBBELL-6KG",
        name="Cast Iron Dumbbell",
        length=Decimal("20.00"),
        width=Decimal("10.00"),
        height=Decimal("10.00"),
        weight=Decimal("6.000"),
    )
    order = Order.objects.create(order_number="ORD-OVERWEIGHT")
    # 2 dumbbells = 12 kg, exceeds 10 kg capacity
    OrderItem.objects.create(order=order, product=dumbbell, quantity=2)

    order, result, _ = evaluate_and_pack_order(order)
    assert order.status == Order.Status.FAILED
    assert "exceeds box maximum capacity" in result.failure_reason


@pytest.mark.django_db
def test_edge_case_multiple_quantities_stacking():
    """Testing an order with multiple quantities of products."""
    box = Box.objects.create(
        name="Medium Box",
        internal_length=Decimal("40.00"),
        internal_width=Decimal("30.00"),
        internal_height=Decimal("20.00"),
        max_weight_capacity=Decimal("10.000"),
        packaging_cost=Decimal("2.50"),
    )
    phone = Product.objects.create(
        sku="PHN-A",
        name="Phone",
        length=Decimal("15.00"),
        width=Decimal("10.00"),
        height=Decimal("2.00"),
        weight=Decimal("0.200"),
    )
    book = Product.objects.create(
        sku="BOK-B",
        name="Book",
        length=Decimal("20.00"),
        width=Decimal("15.00"),
        height=Decimal("3.00"),
        weight=Decimal("0.500"),
    )

    order = Order.objects.create(order_number="ORD-MULTI-QTY")
    OrderItem.objects.create(order=order, product=phone, quantity=5)
    OrderItem.objects.create(order=order, product=book, quantity=3)

    order, result, _ = evaluate_and_pack_order(order)
    assert order.status == Order.Status.EVALUATED
    assert order.selected_box == box
    assert len(result.placed_items_manifest) == 8  # 5 phones + 3 books
