from decimal import Decimal
import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from apps.catalog.models import Box


@pytest.fixture
def auth_user(db):
    return User.objects.create_user(username='box_admin', password='Secr3tPassword!')


@pytest.fixture
def sample_box(db):
    return Box.objects.create(
        name="Test Mailer Box BX-1",
        internal_length=Decimal("22.00"),
        internal_width=Decimal("16.00"),
        internal_height=Decimal("10.00"),
        max_weight_capacity=Decimal("3.500"),
        packaging_cost=Decimal("1.45"),
        is_active=True,
    )


@pytest.mark.django_db
def test_box_list_view_renders(client, sample_box):
    url = reverse('catalog:box_list')
    resp = client.get(url)
    assert resp.status_code == 200
    content = resp.content.decode()
    assert "Shipping Box Inventory" in content
    assert "Test Mailer Box BX-1" in content
    assert "$1.45" in content
    assert "22.00 × 16.00 × 10.00 cm" in content


@pytest.mark.django_db
def test_box_list_status_filter(client, sample_box):
    inactive_box = Box.objects.create(
        name="Decommissioned Heavy Wooden Crate",
        internal_length=Decimal("80.00"),
        internal_width=Decimal("60.00"),
        internal_height=Decimal("50.00"),
        max_weight_capacity=Decimal("50.000"),
        packaging_cost=Decimal("15.00"),
        is_active=False,
    )
    url = reverse('catalog:box_list')

    # Active filter
    resp_active = client.get(f"{url}?status=active")
    assert resp_active.status_code == 200
    content_active = resp_active.content.decode()
    assert "Test Mailer Box BX-1" in content_active
    assert "Decommissioned Heavy Wooden Crate" not in content_active

    # Inactive filter
    resp_inactive = client.get(f"{url}?status=inactive")
    assert resp_inactive.status_code == 200
    content_inactive = resp_inactive.content.decode()
    assert "Decommissioned Heavy Wooden Crate" in content_inactive
    assert "Test Mailer Box BX-1" not in content_inactive


@pytest.mark.django_db
def test_box_create_view_authenticated(client, auth_user):
    client.force_login(auth_user)
    create_url = reverse('catalog:box_create')

    resp_get = client.get(create_url)
    assert resp_get.status_code == 200
    assert "Register Shipping Box Profile" in resp_get.content.decode()

    payload = {
        'name': 'Corrugated Large Cube (BX-CUBE)',
        'internal_length': '40.00',
        'internal_width': '40.00',
        'internal_height': '40.00',
        'max_weight_capacity': '20.000',
        'packaging_cost': '4.25',
        'is_active': 'on',
    }
    resp_post = client.post(create_url, data=payload)
    assert resp_post.status_code == 302
    assert resp_post.url == reverse('catalog:box_list')

    created = Box.objects.get(name='Corrugated Large Cube (BX-CUBE)')
    assert created.volume == Decimal("64000.000")
    assert created.is_active is True


@pytest.mark.django_db
def test_box_update_view_authenticated(client, auth_user, sample_box):
    client.force_login(auth_user)
    edit_url = reverse('catalog:box_edit', kwargs={'pk': sample_box.pk})

    resp_get = client.get(edit_url)
    assert resp_get.status_code == 200

    payload = {
        'name': 'Updated Mailer Box BX-1 Modified',
        'internal_length': '24.00',
        'internal_width': '18.00',
        'internal_height': '12.00',
        'max_weight_capacity': '4.000',
        'packaging_cost': '1.75',
    }
    resp_post = client.post(edit_url, data=payload)
    assert resp_post.status_code == 302
    sample_box.refresh_from_db()
    assert sample_box.name == 'Updated Mailer Box BX-1 Modified'
    assert sample_box.packaging_cost == Decimal("1.75")


@pytest.mark.django_db
def test_box_toggle_active_view(client, auth_user, sample_box):
    client.force_login(auth_user)
    toggle_url = reverse('catalog:box_toggle_active', kwargs={'pk': sample_box.pk})

    assert sample_box.is_active is True
    # Toggle to inactive
    resp = client.post(toggle_url)
    assert resp.status_code == 302
    sample_box.refresh_from_db()
    assert sample_box.is_active is False

    # Toggle back to active
    resp2 = client.post(toggle_url)
    assert resp2.status_code == 302
    sample_box.refresh_from_db()
    assert sample_box.is_active is True


@pytest.mark.django_db
def test_box_delete_view(client, auth_user, sample_box):
    client.force_login(auth_user)
    delete_url = reverse('catalog:box_delete', kwargs={'pk': sample_box.pk})

    resp = client.post(delete_url)
    assert resp.status_code == 302
    assert not Box.objects.filter(pk=sample_box.pk).exists()

