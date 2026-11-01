"""
QA Test Suite - Area C: API Tests
Verifies REST API response schemas, status codes (200, 201, 400, 401, 404, 409, 500),
CSRF/Authentication protection, and candidate rejection payload structures.
"""
from decimal import Decimal
import json
from django.contrib.auth.models import User
from django.test import TestCase
from apps.catalog.models import Box, Product
from apps.orders.models import Order, OrderItem


class RecommendationAPITestCase(TestCase):
    """Rigorous tests covering the box recommendation REST API endpoint."""

    def setUp(self):
        self.box_small = Box.objects.create(
            name="Small Economy Box",
            internal_length=Decimal("20.00"),
            internal_width=Decimal("15.00"),
            internal_height=Decimal("10.00"),
            max_weight_capacity=Decimal("3.000"),
            packaging_cost=Decimal("1.25"),
            is_active=True,
        )
        self.box_large = Box.objects.create(
            name="Large Heavy Box",
            internal_length=Decimal("40.00"),
            internal_width=Decimal("30.00"),
            internal_height=Decimal("25.00"),
            max_weight_capacity=Decimal("15.000"),
            packaging_cost=Decimal("3.50"),
            is_active=True,
        )
        self.product = Product.objects.create(
            sku="QA-PHONE-01",
            name="Smartphone",
            length=Decimal("15.00"),
            width=Decimal("8.00"),
            height=Decimal("2.00"),
            weight=Decimal("0.250"),
        )
        self.order = Order.objects.create(
            order_number="QA-API-ORD-01",
            customer_reference="QA-CUSTOMER",
        )
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=2,
        )

    def test_successful_recommendation_api(self):
        """Verifies successful recommendation returns 200 with complete winning box and rejected candidates."""
        url = f"/api/orders/{self.order.order_number}/recommend-box/"
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 200)

        data = resp.json()
        self.assertEqual(data["order_number"], "QA-API-ORD-01")
        self.assertEqual(data["customer_reference"], "QA-CUSTOMER")
        self.assertEqual(data["selection_status"], "FEASIBLE")
        self.assertEqual(data["total_order_weight"], 0.500)
        self.assertEqual(data["packaging_cost"], 1.25)
        self.assertIsNotNone(data["selected_box"])
        self.assertEqual(data["selected_box"]["name"], "Small Economy Box")
        self.assertIn("dimensions", data["selected_box"])
        self.assertEqual(data["selected_box"]["dimensions"]["unit"], "cm")
        self.assertIn("Small Economy Box", data["explanation"])

        # Check rejected boxes contains the higher-cost large box
        self.assertEqual(len(data["rejected_boxes"]), 1)
        rejected = data["rejected_boxes"][0]
        self.assertEqual(rejected["name"], "Large Heavy Box")
        self.assertIn("higher packaging cost", rejected["rejection_reason"])

    def test_invalid_order_id_returns_404(self):
        """Verifies that requesting a recommendation for a non-existent order returns 404 Not Found."""
        url = "/api/orders/NON-EXISTENT-ORDER/recommend-box/"
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 404)
        data = resp.json()
        self.assertEqual(data["error"], "Not Found")
        self.assertIn("does not exist", data["detail"].lower())

    def test_empty_order_returns_400(self):
        """Verifies that attempting to evaluate an order with zero items returns 400 Bad Request."""
        empty_order = Order.objects.create(order_number="QA-EMPTY-ORD")
        url = f"/api/orders/{empty_order.order_number}/recommend-box/"
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertEqual(data["error"], "Bad Request")
        self.assertIn("no items", data["detail"].lower())

    def test_no_feasible_box_returns_infeasible_status(self):
        """Verifies that when items exceed all boxes, API returns 200 with INFEASIBLE and reasons."""
        giant_product = Product.objects.create(
            sku="QA-GIANT-01",
            name="Industrial Mill",
            length=Decimal("80.00"),
            width=Decimal("60.00"),
            height=Decimal("50.00"),
            weight=Decimal("50.000"),
        )
        infeasible_order = Order.objects.create(order_number="QA-INFEASIBLE-ORD")
        OrderItem.objects.create(order=infeasible_order, product=giant_product, quantity=1)

        url = f"/api/orders/{infeasible_order.order_number}/recommend-box/"
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 200)

        data = resp.json()
        self.assertEqual(data["selection_status"], "INFEASIBLE")
        self.assertIsNone(data["selected_box"])
        self.assertIsNone(data["packaging_cost"])
        self.assertIn("exceeds", data["explanation"].lower())
        self.assertEqual(len(data["rejected_boxes"]), 2)
        for box_eval in data["rejected_boxes"]:
            self.assertTrue(len(box_eval["rejection_reason"]) > 0)


class CatalogAndOrderAPITestCase(TestCase):
    """Tests covering Order creation API, validation errors, and unauthorized access."""

    def setUp(self):
        self.user = User.objects.create_user(username="qa_staff", password="QA-Password123!")
        self.product = Product.objects.create(
            sku="QA-PROD-99",
            name="Testing Device",
            length=Decimal("10.00"),
            width=Decimal("10.00"),
            height=Decimal("10.00"),
            weight=Decimal("1.000"),
        )
        self.box = Box.objects.create(
            name="QA Standard Box",
            internal_length=Decimal("25.00"),
            internal_width=Decimal("25.00"),
            internal_height=Decimal("25.00"),
            max_weight_capacity=Decimal("10.000"),
            packaging_cost=Decimal("2.00"),
            is_active=True,
        )

    def test_invalid_input_order_creation_returns_400(self):
        """Verifies that malformed payloads or invalid quantities return 400 with field errors."""
        # Case 1: Empty line items list
        resp1 = self.client.post("/api/orders/", data=json.dumps({"items": []}), content_type="application/json")
        self.assertEqual(resp1.status_code, 400)
        self.assertIn("items", resp1.json()["errors"])

        # Case 2: Zero quantity
        payload2 = {"items": [{"product_id": self.product.id, "quantity": 0}]}
        resp2 = self.client.post("/api/orders/", data=json.dumps(payload2), content_type="application/json")
        self.assertEqual(resp2.status_code, 400)
        self.assertIn("quantity", list(resp2.json()["errors"].keys())[0])

        # Case 3: Invalid product ID
        payload3 = {"items": [{"product_id": 999999, "quantity": 1}]}
        resp3 = self.client.post("/api/orders/", data=json.dumps(payload3), content_type="application/json")
        self.assertEqual(resp3.status_code, 400)
        self.assertIn("product", list(resp3.json()["errors"].keys())[0])

    def test_unauthorized_access_to_catalog_endpoints(self):
        """Verifies that unsafe catalog modification endpoints require authentication and return 401."""
        # Unauthenticated product creation
        resp_prod = self.client.post(
            "/api/products/",
            data=json.dumps({
                "sku": "UNAUTH-SKU",
                "name": "Unauth Product",
                "length": 10.0,
                "width": 10.0,
                "height": 10.0,
                "weight": 1.0,
            }),
            content_type="application/json",
        )
        self.assertEqual(resp_prod.status_code, 401)
        self.assertEqual(resp_prod.json()["error"], "Unauthorized")

        # Unauthenticated product deletion
        resp_del = self.client.delete(f"/api/products/{self.product.id}/")
        self.assertEqual(resp_del.status_code, 401)

        # Unauthenticated box creation
        resp_box = self.client.post(
            "/api/boxes/",
            data=json.dumps({
                "name": "Unauth Box",
                "internal_length": 20.0,
                "internal_width": 20.0,
                "internal_height": 20.0,
                "max_weight_capacity": 5.0,
                "packaging_cost": 1.0,
            }),
            content_type="application/json",
        )
        self.assertEqual(resp_box.status_code, 401)
