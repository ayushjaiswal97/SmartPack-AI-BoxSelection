from decimal import Decimal
import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from apps.catalog.models import Box, Product
from apps.orders.models import Order, OrderItem


@pytest.fixture
def auth_user(db):
    return User.objects.create_user(username='warehouse_mgr', password='Secr3tPassword!')


@pytest.fixture
def sample_product(db):
    return Product.objects.create(
        sku="TEST-SKU-001",
        name="Industrial Thermal Label Printer",
        length=Decimal("25.00"),
        width=Decimal("18.00"),
        height=Decimal("12.00"),
        weight=Decimal("2.450"),
    )


@pytest.mark.django_db
def test_product_list_view_renders_catalog(client, sample_product):
    url = reverse('catalog:product_list')
    response = client.get(url)
    assert response.status_code == 200
    content = response.content.decode()
    assert "Product Master Catalog" in content
    assert "TEST-SKU-001" in content
    assert "Industrial Thermal Label Printer" in content
    assert "25.00 × 18.00 × 12.00 cm" in content
    assert "2.450 kg" in content


@pytest.mark.django_db
def test_product_list_view_search_filtering(client, sample_product):
    Product.objects.create(
        sku="OTHER-SKU-999",
        name="Barcode Handheld Scanner",
        length=Decimal("15.00"),
        width=Decimal("8.00"),
        height=Decimal("6.00"),
        weight=Decimal("0.350"),
    )
    url = reverse('catalog:product_list')
    
    # Search matching SKU
    resp_search = client.get(f"{url}?q=OTHER")
    assert resp_search.status_code == 200
    content = resp_search.content.decode()
    assert "OTHER-SKU-999" in content
    assert "TEST-SKU-001" not in content

    # Search matching Name
    resp_name = client.get(f"{url}?q=Thermal")
    assert resp_name.status_code == 200
    content_name = resp_name.content.decode()
    assert "TEST-SKU-001" in content_name
    assert "OTHER-SKU-999" not in content_name


@pytest.mark.django_db
def test_product_list_view_sorting(client):
    p1 = Product.objects.create(
        sku="A-SKU",
        name="Alpha",
        length=Decimal("10.00"),
        width=Decimal("10.00"),
        height=Decimal("10.00"),
        weight=Decimal("5.000"),
    )
    p2 = Product.objects.create(
        sku="Z-SKU",
        name="Zulu",
        length=Decimal("5.00"),
        width=Decimal("5.00"),
        height=Decimal("5.00"),
        weight=Decimal("0.500"),
    )

    url = reverse('catalog:product_list')

    # Sort by weight ascending
    resp = client.get(f"{url}?sort=weight")
    assert resp.status_code == 200
    products = list(resp.context['products'])
    assert products[0].sku == "Z-SKU"
    assert products[1].sku == "A-SKU"


@pytest.mark.django_db
def test_product_create_view_authenticated(client, auth_user):
    client.force_login(auth_user)
    create_url = reverse('catalog:product_create')

    # GET returns form
    resp_get = client.get(create_url)
    assert resp_get.status_code == 200
    assert "Register Master Product" in resp_get.content.decode()

    # POST creates product
    payload = {
        'sku': 'NEW-SKU-100',
        'name': 'Ergonomic Packing Tape Dispenser',
        'length': '20.00',
        'width': '10.00',
        'height': '8.00',
        'weight': '0.750',
    }
    resp_post = client.post(create_url, data=payload)
    assert resp_post.status_code == 302
    assert resp_post.url == reverse('catalog:product_list')

    created = Product.objects.get(sku='NEW-SKU-100')
    assert created.name == 'Ergonomic Packing Tape Dispenser'
    assert created.volume == Decimal("1600.000")


@pytest.mark.django_db
def test_product_update_view_authenticated(client, auth_user, sample_product):
    client.force_login(auth_user)
    edit_url = reverse('catalog:product_edit', kwargs={'pk': sample_product.pk})

    resp_get = client.get(edit_url)
    assert resp_get.status_code == 200
    assert "Edit Product Specifications" in resp_get.content.decode()

    payload = {
        'sku': sample_product.sku,
        'name': 'Updated Thermal Printer V2',
        'length': '28.00',
        'width': '19.00',
        'height': '14.00',
        'weight': '2.600',
    }
    resp_post = client.post(edit_url, data=payload)
    assert resp_post.status_code == 302
    sample_product.refresh_from_db()
    assert sample_product.name == 'Updated Thermal Printer V2'
    assert sample_product.length == Decimal("28.00")


@pytest.mark.django_db
def test_product_delete_unlinked_product(client, auth_user, sample_product):
    client.force_login(auth_user)
    delete_url = reverse('catalog:product_delete', kwargs={'pk': sample_product.pk})

    resp = client.post(delete_url)
    assert resp.status_code == 302
    assert not Product.objects.filter(pk=sample_product.pk).exists()


@pytest.mark.django_db
def test_product_delete_protected_when_linked_to_order(client, auth_user, sample_product):
    client.force_login(auth_user)
    
    # Link product to an order item
    order = Order.objects.create(
        order_number="ORD-PROT-TEST",
        status=Order.Status.DRAFT,
    )
    OrderItem.objects.create(
        order=order,
        product=sample_product,
        quantity=3,
    )

    delete_url = reverse('catalog:product_delete', kwargs={'pk': sample_product.pk})
    resp = client.post(delete_url, follow=True)
    assert resp.status_code == 200
    # Must still exist in database
    assert Product.objects.filter(pk=sample_product.pk).exists()
    content = resp.content.decode()
    assert "Cannot delete Product" in content
    assert "linked to historical customer orders" in content
