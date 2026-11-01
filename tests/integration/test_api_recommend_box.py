from decimal import Decimal
from unittest.mock import patch
import pytest
from django.db import DatabaseError
from django.urls import reverse
from apps.catalog.models import Box, Product
from apps.orders.models import Order, OrderItem


@pytest.mark.django_db
def test_api_recommend_box_success_with_id(client):
    """Successful box recommendation by primary key ID."""
    box_small = Box.objects.create(
        name="Small Box (BX-SM)",
        internal_length=Decimal("20.00"),
        internal_width=Decimal("15.00"),
        internal_height=Decimal("10.00"),
        max_weight_capacity=Decimal("3.000"),
        packaging_cost=Decimal("1.50"),
    )
    box_large = Box.objects.create(
        name="Large Box (BX-LG)",
        internal_length=Decimal("50.00"),
        internal_width=Decimal("40.00"),
        internal_height=Decimal("30.00"),
        max_weight_capacity=Decimal("15.000"),
        packaging_cost=Decimal("4.50"),
    )
    phone = Product.objects.create(
        sku="ELEC-PHN-TEST",
        name="Smartphone",
        length=Decimal("15.00"),
        width=Decimal("8.00"),
        height=Decimal("2.00"),
        weight=Decimal("0.250"),
    )
    order = Order.objects.create(order_number="ORD-API-001", customer_reference="ACME Corp")
    OrderItem.objects.create(order=order, product=phone, quantity=2)

    url = f"/api/orders/{order.id}/recommend-box/"
    response = client.post(url)

    assert response.status_code == 200
    data = response.json()

    assert data["order_number"] == "ORD-API-001"
    assert data["customer_reference"] == "ACME Corp"
    assert data["selection_status"] == "FEASIBLE"
    assert data["total_order_weight"] == 0.500
    assert data["packaging_cost"] == 1.50

    # Selected box details
    selected_box = data["selected_box"]
    assert selected_box is not None
    assert selected_box["id"] == box_small.id
    assert selected_box["name"] == "Small Box (BX-SM)"
    assert selected_box["dimensions"]["length"] == 20.0
    assert selected_box["dimensions"]["width"] == 15.0
    assert selected_box["dimensions"]["height"] == 10.0
    assert selected_box["max_weight_capacity"] == 3.0
    assert selected_box["packaging_cost"] == 1.50

    # Rejected boxes list
    assert len(data["rejected_boxes"]) == 1
    rejected = data["rejected_boxes"][0]
    assert rejected["id"] == box_large.id
    assert "higher packaging cost" in rejected["rejection_reason"]


@pytest.mark.django_db
def test_api_recommend_box_success_with_order_number(client):
    """Successful recommendation accessed via order_number string identifier."""
    Box.objects.create(
        name="Universal Box",
        internal_length=Decimal("30.00"),
        internal_width=Decimal("20.00"),
        internal_height=Decimal("15.00"),
        max_weight_capacity=Decimal("5.000"),
        packaging_cost=Decimal("2.00"),
    )
    product = Product.objects.create(
        sku="ITEM-STR",
        name="Item",
        length=Decimal("10.00"),
        width=Decimal("10.00"),
        height=Decimal("5.00"),
        weight=Decimal("0.500"),
    )
    order = Order.objects.create(order_number="ORD-STR-TEST")
    OrderItem.objects.create(order=order, product=product, quantity=1)

    url = f"/api/orders/{order.order_number}/recommend-box/"
    response = client.post(url)

    assert response.status_code == 200
    assert response.json()["selection_status"] == "FEASIBLE"


@pytest.mark.django_db
def test_api_recommend_box_invalid_order_id(client):
    """Attempting to evaluate a non-existent order returns 404 Not Found."""
    url = "/api/orders/99999999/recommend-box/"
    response = client.post(url)

    assert response.status_code == 404
    data = response.json()
    assert data["error"] == "Not Found"
    assert "Order '99999999' does not exist." in data["detail"]


@pytest.mark.django_db
def test_api_recommend_box_empty_order(client):
    """An order with no line items returns 400 Bad Request."""
    order = Order.objects.create(order_number="ORD-EMPTY-001")

    url = f"/api/orders/{order.id}/recommend-box/"
    response = client.post(url)

    assert response.status_code == 400
    data = response.json()
    assert data["error"] == "Bad Request"
    assert "contains no items" in data["detail"]


@pytest.mark.django_db
def test_api_recommend_box_infeasible_order(client):
    """When items cannot fit into any active box, returns 200 with INFEASIBLE status and reasons."""
    Box.objects.create(
        name="Small Box",
        internal_length=Decimal("10.00"),
        internal_width=Decimal("10.00"),
        internal_height=Decimal("10.00"),
        max_weight_capacity=Decimal("2.000"),
        packaging_cost=Decimal("1.00"),
    )
    oversized_item = Product.objects.create(
        sku="OVERSIZED-01",
        name="Oversized Pole",
        length=Decimal("100.00"),
        width=Decimal("5.00"),
        height=Decimal("5.00"),
        weight=Decimal("1.000"),
    )
    order = Order.objects.create(order_number="ORD-INFEASIBLE-001")
    OrderItem.objects.create(order=order, product=oversized_item, quantity=1)

    url = f"/api/orders/{order.id}/recommend-box/"
    response = client.post(url)

    assert response.status_code == 200
    data = response.json()

    assert data["selection_status"] == "INFEASIBLE"
    assert data["selected_box"] is None
    assert data["packaging_cost"] is None
    assert "cannot fit" in data["explanation"].lower() or "exceed" in data["explanation"].lower()
    assert len(data["rejected_boxes"]) == 1
    assert "exceed" in data["rejected_boxes"][0]["rejection_reason"].lower()


@pytest.mark.django_db
def test_api_recommend_box_ignores_inactive_boxes(client):
    """Inactive boxes are not selected even if they are cheaper and physically viable."""
    # Cheap inactive box
    Box.objects.create(
        name="Cheaper Inactive Box",
        internal_length=Decimal("30.00"),
        internal_width=Decimal("30.00"),
        internal_height=Decimal("30.00"),
        max_weight_capacity=Decimal("10.000"),
        packaging_cost=Decimal("0.50"),
        is_active=False,
    )
    # Active standard box
    active_box = Box.objects.create(
        name="Active Box",
        internal_length=Decimal("30.00"),
        internal_width=Decimal("30.00"),
        internal_height=Decimal("30.00"),
        max_weight_capacity=Decimal("10.000"),
        packaging_cost=Decimal("2.50"),
        is_active=True,
    )
    product = Product.objects.create(
        sku="ITEM-ACTIVE",
        name="Item",
        length=Decimal("10.00"),
        width=Decimal("10.00"),
        height=Decimal("10.00"),
        weight=Decimal("1.000"),
    )
    order = Order.objects.create(order_number="ORD-ACTIVE-TEST")
    OrderItem.objects.create(order=order, product=product, quantity=1)

    url = f"/api/orders/{order.id}/recommend-box/"
    response = client.post(url)

    assert response.status_code == 200
    data = response.json()
    assert data["selected_box"]["id"] == active_box.id
    assert data["selected_box"]["packaging_cost"] == 2.50


@pytest.mark.django_db
def test_api_recommend_box_database_error_handling(client):
    """DatabaseError during packaging persistence returns 500 Internal Server Error."""
    order = Order.objects.create(order_number="ORD-DB-ERR")
    prod = Product.objects.create(
        sku="ITEM-DB",
        name="Item",
        length=Decimal("10.00"),
        width=Decimal("10.00"),
        height=Decimal("10.00"),
        weight=Decimal("1.000"),
    )
    OrderItem.objects.create(order=order, product=prod, quantity=1)

    with patch("apps.orders.services.transaction.atomic", side_effect=DatabaseError("DB connection lost")):
        url = f"/api/orders/{order.id}/recommend-box/"
        response = client.post(url)

        assert response.status_code == 500
        data = response.json()
        assert data["error"] == "Internal Server Error"
        assert "database error occurred" in data["detail"]

