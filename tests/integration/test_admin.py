from decimal import Decimal
import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from apps.catalog.models import Box, Product
from apps.orders.models import Order, OrderItem


@pytest.fixture
def admin_client(client):
    admin_user = User.objects.create_superuser(
        username="test_admin",
        password="test_password_123",
        email="admin@test.com",
    )
    client.login(username="test_admin", password="test_password_123")
    return client


@pytest.mark.django_db
def test_admin_changelist_views_load(admin_client):
    """Ensure all model changelist pages in Django admin load with 200 OK."""
    urls = [
        reverse("admin:catalog_product_changelist"),
        reverse("admin:catalog_box_changelist"),
        reverse("admin:orders_order_changelist"),
        reverse("admin:orders_orderitem_changelist"),
        reverse("admin:orders_packingresult_changelist"),
    ]
    for url in urls:
        response = admin_client.get(url)
        assert response.status_code == 200


@pytest.mark.django_db
def test_admin_box_actions(admin_client):
    """Test activating and deactivating shipping boxes via admin action."""
    box = Box.objects.create(
        name="Test Box",
        internal_length=Decimal("20.00"),
        internal_width=Decimal("20.00"),
        internal_height=Decimal("20.00"),
        max_weight_capacity=Decimal("5.000"),
        packaging_cost=Decimal("2.00"),
        is_active=True,
    )
    url = reverse("admin:catalog_box_changelist")

    # Deactivate action
    admin_client.post(url, {
        "action": "deactivate_boxes",
        "_selected_action": [str(box.id)],
    })
    box.refresh_from_db()
    assert box.is_active is False

    # Activate action
    admin_client.post(url, {
        "action": "activate_boxes",
        "_selected_action": [str(box.id)],
    })
    box.refresh_from_db()
    assert box.is_active is True


@pytest.mark.django_db
def test_admin_order_evaluate_action(admin_client):
    """Test running box recommendation action on selected orders in admin."""
    box = Box.objects.create(
        name="Standard Box",
        internal_length=Decimal("30.00"),
        internal_width=Decimal("20.00"),
        internal_height=Decimal("15.00"),
        max_weight_capacity=Decimal("5.000"),
        packaging_cost=Decimal("2.50"),
    )
    product = Product.objects.create(
        sku="SKU-ADMIN-TEST",
        name="Test Gadget",
        length=Decimal("10.00"),
        width=Decimal("10.00"),
        height=Decimal("5.00"),
        weight=Decimal("0.500"),
    )
    order = Order.objects.create(order_number="ORD-ADMIN-01")
    OrderItem.objects.create(order=order, product=product, quantity=2)

    url = reverse("admin:orders_order_changelist")
    response = admin_client.post(url, {
        "action": "evaluate_box_selection",
        "_selected_action": [str(order.id)],
    }, follow=True)

    assert response.status_code == 200
    order.refresh_from_db()
    assert order.status == Order.Status.EVALUATED
    assert order.selected_box == box
    assert order.packaging_cost == Decimal("2.50")


@pytest.mark.django_db
def test_admin_order_mark_as_packed_action(admin_client):
    """Test marking orders as packed via admin action."""
    order = Order.objects.create(order_number="ORD-PACK-01", status=Order.Status.EVALUATED)
    url = reverse("admin:orders_order_changelist")

    admin_client.post(url, {
        "action": "mark_as_packed",
        "_selected_action": [str(order.id)],
    })

    order.refresh_from_db()
    assert order.status == Order.Status.PACKED

