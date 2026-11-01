from decimal import Decimal
import pytest
from django.urls import reverse
from apps.catalog.models import Box, Product
from apps.orders.models import Order, OrderItem


@pytest.mark.django_db
def test_dashboard_get_view(client):
    response = client.get(reverse('orders:dashboard'))
    assert response.status_code == 200
    assert 'Warehouse Operations Console' in response.content.decode()
    assert 'Master Catalog SKUs' in response.content.decode()


@pytest.mark.django_db
def test_simulator_get_view(client):
    response = client.get(reverse('orders:simulator'))
    assert response.status_code == 200
    assert 'AI-Assisted Box Selection Simulator' in response.content.decode()


@pytest.mark.django_db
def test_simulator_post_successful_evaluation(client):
    # Setup catalog
    box = Box.objects.create(
        name="Standard Box",
        internal_length=Decimal("30.00"),
        internal_width=Decimal("20.00"),
        internal_height=Decimal("15.00"),
        max_weight_capacity=Decimal("5.000"),
        packaging_cost=Decimal("2.00"),
    )
    product = Product.objects.create(
        sku="TEST-SKU-1",
        name="Test Gadget",
        length=Decimal("10.00"),
        width=Decimal("8.00"),
        height=Decimal("5.00"),
        weight=Decimal("0.500"),
    )

    # Submit order simulation
    data = {
        'items-TOTAL_FORMS': '1',
        'items-INITIAL_FORMS': '0',
        'items-MIN_NUM_FORMS': '1',
        'items-MAX_NUM_FORMS': '1000',
        'items-0-product': str(product.id),
        'items-0-quantity': '2',
        'notes': 'Test simulation submission',
    }

    response = client.post(reverse('orders:simulator'), data=data)
    assert response.status_code == 302
    assert '/recommendation/' in response.url

    # Check database state
    order = Order.objects.first()
    assert order is not None
    assert order.status == Order.Status.EVALUATED
    assert order.selected_box == box
    assert order.packaging_cost == Decimal("2.00")


@pytest.mark.django_db
def test_simulator_post_no_items_validation_error(client):
    data = {
        'items-TOTAL_FORMS': '1',
        'items-INITIAL_FORMS': '0',
        'items-MIN_NUM_FORMS': '1',
        'items-MAX_NUM_FORMS': '1000',
        'items-0-product': '',
        'items-0-quantity': '1',
    }
    response = client.post(reverse('orders:simulator'), data=data)
    assert response.status_code == 200
    assert 'Please correct the errors' in response.content.decode() or 'Please add at least one' in response.content.decode()


@pytest.mark.django_db
def test_recommendation_view(client):
    box = Box.objects.create(
        name="Mailer Box",
        internal_length=Decimal("20.00"),
        internal_width=Decimal("15.00"),
        internal_height=Decimal("10.00"),
        max_weight_capacity=Decimal("2.000"),
        packaging_cost=Decimal("1.20"),
    )
    order = Order.objects.create(
        order_number="ORD-REC-TEST",
        status=Order.Status.EVALUATED,
        selected_box=box,
        packaging_cost=Decimal("1.20"),
    )
    response = client.get(reverse('orders:recommendation', kwargs={'order_number': order.order_number}))
    assert response.status_code == 200
    assert "Mailer Box" in response.content.decode()
    assert "₹1.20" in response.content.decode()


@pytest.mark.django_db
def test_order_list_and_detail_views(client):
    order = Order.objects.create(
        order_number="ORD-DETAIL-TEST",
        customer_reference="VIP-ACME-CORP",
        status=Order.Status.DRAFT,
    )
    # Order list
    resp_list = client.get(reverse('orders:order_list'))
    assert resp_list.status_code == 200
    assert "ORD-DETAIL-TEST" in resp_list.content.decode()
    assert "VIP-ACME-CORP" in resp_list.content.decode()

    # Order detail
    resp_detail = client.get(reverse('orders:order_detail', kwargs={'order_number': order.order_number}))
    assert resp_detail.status_code == 200
    assert "ORD-DETAIL-TEST" in resp_detail.content.decode()
    assert "VIP-ACME-CORP" in resp_detail.content.decode()


@pytest.mark.django_db
def test_recommendation_history_view(client):
    box = Box.objects.create(
        name="History Audit Box",
        internal_length=Decimal("30.00"),
        internal_width=Decimal("20.00"),
        internal_height=Decimal("15.00"),
        max_weight_capacity=Decimal("10.000"),
        packaging_cost=Decimal("2.50"),
    )
    order = Order.objects.create(
        order_number="ORD-HIST-001",
        customer_reference="LOGS-AUDIT",
        status=Order.Status.EVALUATED,
        selected_box=box,
        packaging_cost=Decimal("2.50"),
    )
    resp = client.get(reverse('orders:history_list'))
    assert resp.status_code == 200
    content = resp.content.decode()
    assert "Recommendation History" in content
    assert "ORD-HIST-001" in content
    assert "History Audit Box" in content
    assert "₹2.50" in content


@pytest.mark.django_db
def test_catalog_views(client):
    response = client.get(reverse('catalog:product_list'))
    assert response.status_code == 200

    response = client.get(reverse('catalog:box_list'))
    assert response.status_code == 200


@pytest.mark.django_db
def test_catalog_create_requires_login(client):
    # Unauthenticated user redirected to login
    response = client.get(reverse('catalog:product_create'))
    assert response.status_code == 302
    assert '/accounts/login/' in response.url

    response = client.get(reverse('catalog:box_create'))
    assert response.status_code == 302
    assert '/accounts/login/' in response.url
