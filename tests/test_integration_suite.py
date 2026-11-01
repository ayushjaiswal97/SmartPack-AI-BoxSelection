"""
QA Test Suite - Area D: Integration Tests
Verifies database-to-service mapping, atomic state persistence,
end-to-end API response contract validation, and deterministic result consistency.
"""
from decimal import Decimal
from django.test import TestCase
from apps.catalog.models import Box, Product
from apps.orders.models import Order, OrderItem, PackingResult
from apps.orders.services import (
    PackagingService,
    build_box_dtos,
    build_item_dtos_from_order,
)


class DatabaseToServiceIntegrationTestCase(TestCase):
    """Verifies seamless data layer integration between ORM models and pure DTOs."""

    def setUp(self):
        self.p1 = Product.objects.create(
            sku="INTEG-P1",
            name="Keyboard",
            length=Decimal("45.00"),
            width=Decimal("15.00"),
            height=Decimal("4.00"),
            weight=Decimal("0.850"),
        )
        self.p2 = Product.objects.create(
            sku="INTEG-P2",
            name="Mouse",
            length=Decimal("12.00"),
            width=Decimal("7.00"),
            height=Decimal("4.00"),
            weight=Decimal("0.120"),
        )
        self.box_active = Box.objects.create(
            name="Active Dispatch Box",
            internal_length=Decimal("50.00"),
            internal_width=Decimal("30.00"),
            internal_height=Decimal("20.00"),
            max_weight_capacity=Decimal("10.000"),
            packaging_cost=Decimal("2.50"),
            is_active=True,
        )
        self.box_inactive = Box.objects.create(
            name="Decommissioned Box",
            internal_length=Decimal("60.00"),
            internal_width=Decimal("40.00"),
            internal_height=Decimal("30.00"),
            max_weight_capacity=Decimal("20.000"),
            packaging_cost=Decimal("1.00"),
            is_active=False,
        )
        self.order = Order.objects.create(
            order_number="ORD-INTEG-001",
            customer_reference="LOGISTICS-PARTNER",
        )
        OrderItem.objects.create(order=self.order, product=self.p1, quantity=1)
        OrderItem.objects.create(order=self.order, product=self.p2, quantity=2)

    def test_database_to_service_dto_expansion(self):
        """Verifies ORM models expand correctly into discrete ItemDTOs with quantity multipliers."""
        item_dtos = build_item_dtos_from_order(self.order)
        # 1 keyboard + 2 mice = 3 discrete items
        self.assertEqual(len(item_dtos), 3)

        keyboard_dtos = [i for i in item_dtos if i.sku == "INTEG-P1"]
        mouse_dtos = [i for i in item_dtos if i.sku == "INTEG-P2"]
        self.assertEqual(len(keyboard_dtos), 1)
        self.assertEqual(len(mouse_dtos), 2)
        self.assertEqual(keyboard_dtos[0].length, Decimal("45.00"))
        self.assertEqual(mouse_dtos[0].weight, Decimal("0.120"))

    def test_database_to_service_box_filtering(self):
        """Verifies build_box_dtos filters out inactive shipping containers by default."""
        boxes = build_box_dtos(active_only=True)
        self.assertEqual(len(boxes), 1)
        self.assertEqual(boxes[0].name, "Active Dispatch Box")

        all_boxes = build_box_dtos(active_only=False)
        self.assertEqual(len(all_boxes), 2)


class ServicePersistenceAndConsistencyTestCase(TestCase):
    """Verifies atomic ORM persistence and deterministic result consistency."""

    def setUp(self):
        self.box_small = Box.objects.create(
            name="Tier 1 Mailer",
            internal_length=Decimal("25.00"),
            internal_width=Decimal("20.00"),
            internal_height=Decimal("10.00"),
            max_weight_capacity=Decimal("3.000"),
            packaging_cost=Decimal("1.50"),
            is_active=True,
        )
        self.box_medium = Box.objects.create(
            name="Tier 2 Medium Box",
            internal_length=Decimal("35.00"),
            internal_width=Decimal("25.00"),
            internal_height=Decimal("15.00"),
            max_weight_capacity=Decimal("8.000"),
            packaging_cost=Decimal("2.25"),
            is_active=True,
        )
        self.product = Product.objects.create(
            sku="INTEG-ITEM-01",
            name="Retail Boxed Gadget",
            length=Decimal("18.00"),
            width=Decimal("12.00"),
            height=Decimal("6.00"),
            weight=Decimal("0.800"),
        )
        self.order = Order.objects.create(
            order_number="ORD-INTEG-PERSIST",
            customer_reference="VIP-ACME-CORP",
            status=Order.Status.DRAFT,
        )
        OrderItem.objects.create(order=self.order, product=self.product, quantity=2)

    def test_order_to_packaging_service_atomic_persistence(self):
        """Verifies service call transitions order status and creates linked PackingResult row."""
        result_payload = PackagingService.recommend_box_for_order(self.order.id)
        self.assertEqual(result_payload["selection_status"], "FEASIBLE")

        # Reload order from database
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.EVALUATED)
        self.assertIsNotNone(self.order.selected_box)
        self.assertEqual(self.order.selected_box, self.box_medium)
        self.assertEqual(self.order.packaging_cost, Decimal("2.25"))
        self.assertEqual(self.order.total_weight, Decimal("1.600"))

        # Verify 1-to-1 linked PackingResult persistence
        self.assertTrue(hasattr(self.order, 'packing_result'))
        packing_res = self.order.packing_result
        self.assertTrue(packing_res.is_feasible)
        self.assertGreater(packing_res.volume_utilization_pct, Decimal("0.00"))
        self.assertEqual(len(packing_res.placed_items_manifest), 2)
        for placement in packing_res.placed_items_manifest:
            self.assertIn("x", placement)
            self.assertIn("y", placement)
            self.assertIn("z", placement)
            self.assertIn("dx", placement)
            self.assertIn("dy", placement)
            self.assertIn("dz", placement)

    def test_api_response_structure_contract(self):
        """Verifies that the service output adheres exactly to the expected JSON response contract."""
        data = PackagingService.recommend_box_for_order(self.order.order_number)

        expected_top_keys = [
            "order_number",
            "customer_reference",
            "selection_status",
            "total_order_weight",
            "total_order_volume",
            "selected_box",
            "packaging_cost",
            "volume_utilization_pct",
            "weight_utilization_pct",
            "explanation",
            "rejected_boxes",
            "placed_items",
            "execution_time_ms",
        ]
        for key in expected_top_keys:
            self.assertIn(key, data, f"Missing required response key: '{key}'")

        # Check selected box structure
        box_data = data["selected_box"]
        self.assertIsInstance(box_data["id"], int)
        self.assertIsInstance(box_data["name"], str)
        self.assertIsInstance(box_data["dimensions"], dict)
        self.assertIn("length", box_data["dimensions"])
        self.assertIn("width", box_data["dimensions"])
        self.assertIn("height", box_data["dimensions"])
        self.assertIn("unit", box_data["dimensions"])
        self.assertIsInstance(box_data["max_weight_capacity"], float)
        self.assertIsInstance(box_data["packaging_cost"], float)

        # Check rejected boxes structure
        self.assertIsInstance(data["rejected_boxes"], list)
        for r_box in data["rejected_boxes"]:
            self.assertIn("id", r_box)
            self.assertIn("name", r_box)
            self.assertIn("dimensions", r_box)
            self.assertIn("max_weight_capacity", r_box)
            self.assertIn("packaging_cost", r_box)
            self.assertIn("rejection_reason", r_box)

    def test_recommendation_results_consistency(self):
        """
        Consistency requirement:
        Executing recommendation multiple times on identical input must produce
        100% deterministic winning box choice, cost, and placement coordinates.
        """
        runs = []
        for _ in range(5):
            res = PackagingService.recommend_box_for_order(self.order.order_number)
            runs.append(res)

        baseline = runs[0]
        for idx, run in enumerate(runs[1:], start=2):
            self.assertEqual(
                run["selected_box"]["id"],
                baseline["selected_box"]["id"],
                f"Run #{idx} selected different box ID",
            )
            self.assertEqual(
                run["packaging_cost"],
                baseline["packaging_cost"],
                f"Run #{idx} returned different packaging cost",
            )
            self.assertEqual(
                run["placed_items"],
                baseline["placed_items"],
                f"Run #{idx} returned different spatial placements",
            )
