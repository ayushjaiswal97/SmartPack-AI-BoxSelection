from decimal import Decimal
import json
import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from apps.catalog.models import Box, Product
from apps.orders.models import Order, OrderItem


@pytest.fixture
def auth_user(db):
    return User.objects.create_user(username='api_operator', password='Password123!')


@pytest.fixture
def sample_product(db):
    return Product.objects.create(
        sku="API-PROD-01",
        name="Industrial RFID Reader",
        length=Decimal("20.00"),
        width=Decimal("15.00"),
        height=Decimal("10.00"),
        weight=Decimal("1.250"),
    )


@pytest.fixture
def sample_box(db):
    return Box.objects.create(
        name="Standard API Shipping Box",
        internal_length=Decimal("30.00"),
        internal_width=Decimal("25.00"),
        internal_height=Decimal("20.00"),
        max_weight_capacity=Decimal("10.000"),
        packaging_cost=Decimal("2.25"),
        is_active=True,
    )


@pytest.mark.django_db
def test_product_api_list_and_create(client, auth_user, sample_product):
    # GET list
    resp = client.get('/api/products/')
    assert resp.status_code == 200
    data = resp.json()
    assert data['count'] >= 1
    assert data['products'][0]['sku'] == sample_product.sku

    # POST unauthenticated returns 401
    payload = {
        "sku": "NEW-API-SKU",
        "name": "Barcode Scanner Pro",
        "length": 18.0,
        "width": 12.0,
        "height": 8.0,
        "weight": 0.650,
    }
    resp_unauth = client.post('/api/products/', data=json.dumps(payload), content_type='application/json')
    assert resp_unauth.status_code == 401

    # POST authenticated creates product (201)
    client.force_login(auth_user)
    resp_create = client.post('/api/products/', data=json.dumps(payload), content_type='application/json')
    assert resp_create.status_code == 201
    created_data = resp_create.json()
    assert created_data['product']['sku'] == "NEW-API-SKU"

    # POST invalid data returns 400 with field errors
    invalid_payload = {
        "sku": "",  # Blank SKU
        "name": "Invalid Product",
        "length": -5.0,  # Negative length
        "width": 10.0,
        "height": 10.0,
        "weight": 1.0,
    }
    resp_invalid = client.post('/api/products/', data=json.dumps(invalid_payload), content_type='application/json')
    assert resp_invalid.status_code == 400
    err_data = resp_invalid.json()
    assert "errors" in err_data
    assert "sku" in err_data["errors"]


@pytest.mark.django_db
def test_product_api_detail_update_delete(client, auth_user, sample_product):
    client.force_login(auth_user)

    # GET detail
    resp = client.get(f'/api/products/{sample_product.id}/')
    assert resp.status_code == 200
    assert resp.json()['product']['sku'] == sample_product.sku

    # GET non-existent returns 404
    resp_404 = client.get('/api/products/999999/')
    assert resp_404.status_code == 404

    # PUT update
    update_payload = {
        "sku": sample_product.sku,
        "name": "Updated RFID Reader V2",
        "length": 22.0,
        "width": 16.0,
        "height": 11.0,
        "weight": 1.400,
    }
    resp_update = client.put(f'/api/products/{sample_product.id}/', data=json.dumps(update_payload), content_type='application/json')
    assert resp_update.status_code == 200
    assert resp_update.json()['product']['name'] == "Updated RFID Reader V2"

    # DELETE product returns 200
    resp_del = client.delete(f'/api/products/{sample_product.id}/')
    assert resp_del.status_code == 200
    assert not Product.objects.filter(id=sample_product.id).exists()


@pytest.mark.django_db
def test_product_api_delete_conflict_409_when_linked(client, auth_user, sample_product):
    client.force_login(auth_user)

    # Link product to order item
    order = Order.objects.create(order_number="ORD-API-CONFLICT", status=Order.Status.DRAFT)
    OrderItem.objects.create(order=order, product=sample_product, quantity=1)

    # DELETE returns 409 Conflict
    resp_del = client.delete(f'/api/products/{sample_product.id}/')
    assert resp_del.status_code == 409
    assert "Conflict" in resp_del.json()['error']
    assert Product.objects.filter(id=sample_product.id).exists()


@pytest.mark.django_db
def test_box_api_crud_and_toggle(client, auth_user, sample_box):
    # GET list
    resp = client.get('/api/boxes/')
    assert resp.status_code == 200
    assert resp.json()['count'] >= 1

    # POST create (auth)
    client.force_login(auth_user)
    new_box_data = {
        "name": "Extra Large Warehouse Crate",
        "internal_length": 50.0,
        "internal_width": 40.0,
        "internal_height": 30.0,
        "max_weight_capacity": 25.0,
        "packaging_cost": 5.50,
        "is_active": True,
    }
    resp_create = client.post('/api/boxes/', data=json.dumps(new_box_data), content_type='application/json')
    assert resp_create.status_code == 201
    created_box_id = resp_create.json()['box']['id']

    # Toggle active
    resp_toggle = client.post(f'/api/boxes/{created_box_id}/toggle-active/')
    assert resp_toggle.status_code == 200
    assert resp_toggle.json()['box']['is_active'] is False

    # DELETE box
    resp_del = client.delete(f'/api/boxes/{created_box_id}/')
    assert resp_del.status_code == 200
    assert not Box.objects.filter(id=created_box_id).exists()


@pytest.mark.django_db
def test_order_api_create_and_evaluate(client, sample_product, sample_box):
    # Create order via API with items
    payload = {
        "customer_reference": "CUST-REST-01",
        "notes": "Handle with care",
        "items": [
            {"product_id": sample_product.id, "quantity": 2}
        ]
    }
    resp = client.post('/api/orders/', data=json.dumps(payload), content_type='application/json')
    assert resp.status_code == 201
    order_data = resp.json()['order']
    assert order_data['customer_reference'] == "CUST-REST-01"
    assert order_data['status'] == Order.Status.EVALUATED
    assert order_data['selected_box'] == sample_box.name

    # GET order detail
    resp_detail = client.get(f"/api/orders/{order_data['order_number']}/")
    assert resp_detail.status_code == 200
    assert resp_detail.json()['order']['order_number'] == order_data['order_number']


@pytest.mark.django_db
def test_order_api_create_validation_failure(client):
    # Empty items returns 400
    resp_empty = client.post('/api/orders/', data=json.dumps({"items": []}), content_type='application/json')
    assert resp_empty.status_code == 400

    # Non-existent product ID returns 400
    resp_invalid = client.post(
        '/api/orders/',
        data=json.dumps({"items": [{"product_id": 99999, "quantity": 1}]}),
        content_type='application/json',
    )
    assert resp_invalid.status_code == 400
    assert "errors" in resp_invalid.json()

