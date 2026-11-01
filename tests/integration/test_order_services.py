from decimal import Decimal
import pytest
from apps.catalog.models import Product, ShippingBox
from apps.orders.models import Order, OrderItem
from apps.orders.services import evaluate_and_pack_order


@pytest.mark.django_db
def test_order_evaluation_and_box_recommendation():
    # Setup candidate boxes
    small_box = ShippingBox.objects.create(
        name="Small Box",
        internal_length=Decimal("20.00"),
        internal_width=Decimal("15.00"),
        internal_height=Decimal("10.00"),
        max_weight_capacity=Decimal("3.000"),
        packaging_cost=Decimal("1.50"),
    )
    large_box = ShippingBox.objects.create(
        name="Large Box",
        internal_length=Decimal("50.00"),
        internal_width=Decimal("40.00"),
        internal_height=Decimal("30.00"),
        max_weight_capacity=Decimal("15.000"),
        packaging_cost=Decimal("4.50"),
    )

    # Setup products
    phone = Product.objects.create(
        sku="PHN-01",
        name="Phone",
        length=Decimal("15.00"),
        width=Decimal("8.00"),
        height=Decimal("2.00"),
        weight=Decimal("0.200"),
    )

    # Create Order
    order = Order.objects.create(order_number="ORD-TEST-001")
    OrderItem.objects.create(order=order, product=phone, quantity=2)

    # Evaluate
    updated_order, result, _ = evaluate_and_pack_order(order)

    assert updated_order.status == Order.STATUS_EVALUATED
    assert updated_order.selected_box == small_box
    assert updated_order.packaging_cost == Decimal("1.50")
    assert result.is_feasible is True
    assert len(result.placed_items_manifest) == 2
    assert result.volume_utilization_pct > Decimal("0.00")


@pytest.mark.django_db
def test_order_evaluation_infeasible_oversized():
    ShippingBox.objects.create(
        name="Small Box",
        internal_length=Decimal("20.00"),
        internal_width=Decimal("15.00"),
        internal_height=Decimal("10.00"),
        max_weight_capacity=Decimal("3.000"),
        packaging_cost=Decimal("1.50"),
    )
    # Item volume is 25x2x2 = 100 cm³ (well within 3000 cm³), but length 25cm exceeds max box length 20cm
    oversized_item = Product.objects.create(
        sku="LONG-ROD-01",
        name="Long Rod",
        length=Decimal("25.00"),
        width=Decimal("2.00"),
        height=Decimal("2.00"),
        weight=Decimal("0.500"),
    )
    order = Order.objects.create(order_number="ORD-TEST-OVERSIZE")
    OrderItem.objects.create(order=order, product=oversized_item, quantity=1)

    updated_order, result, _ = evaluate_and_pack_order(order)

    assert updated_order.status == Order.STATUS_FAILED
    assert updated_order.selected_box is None
    assert result.is_feasible is False
    assert "cannot fit inside box" in result.failure_reason


@pytest.mark.django_db
def test_order_item_snapshot_immutability():
    prod = Product.objects.create(
        sku="SNAP-01",
        name="Original Product",
        length=Decimal("10.00"),
        width=Decimal("10.00"),
        height=Decimal("10.00"),
        weight=Decimal("1.000"),
    )
    order = Order.objects.create(order_number="ORD-SNAPSHOT")
    item = OrderItem.objects.create(order=order, product=prod, quantity=1)

    assert item.unit_length_snapshot == Decimal("10.00")

    # Modify catalog product
    prod.length = Decimal("99.00")
    prod.save()

    # Refetch item from DB
    item.refresh_from_db()
    assert item.unit_length_snapshot == Decimal("10.00")
