"""
QA Test Suite - Area A: Model Tests
Verifies database integrity, check constraints, uniqueness, positive bounds, and field validations.
"""
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from apps.catalog.models import Box, Product
from apps.orders.models import Order, OrderItem


class ProductModelTestCase(TestCase):
    """Automated test cases covering Product entity integrity and constraints."""

    def test_product_creation_with_valid_attributes(self):
        """Verifies that a Product can be successfully persisted with valid physical dimensions."""
        product = Product.objects.create(
            sku="QA-SKU-100",
            name="Industrial Barcode Scanner",
            length=Decimal("20.50"),
            width=Decimal("15.25"),
            height=Decimal("10.00"),
            weight=Decimal("1.250"),
        )
        self.assertIsNotNone(product.pk)
        self.assertEqual(product.sku, "QA-SKU-100")
        self.assertEqual(product.name, "Industrial Barcode Scanner")
        self.assertEqual(product.length, Decimal("20.50"))
        self.assertEqual(product.width, Decimal("15.25"))
        self.assertEqual(product.height, Decimal("10.00"))
        self.assertEqual(product.weight, Decimal("1.250"))
        self.assertEqual(product.volume, Decimal("3126.250"))
        self.assertIn("QA-SKU-100", str(product))

    def test_unique_sku_validation(self):
        """Ensures duplicate SKU codes cannot be registered across catalog products."""
        Product.objects.create(
            sku="UNIQUE-SKU-001",
            name="Product Alpha",
            length=Decimal("10.00"),
            width=Decimal("10.00"),
            height=Decimal("10.00"),
            weight=Decimal("1.000"),
        )
        duplicate = Product(
            sku="UNIQUE-SKU-001",
            name="Product Beta",
            length=Decimal("12.00"),
            width=Decimal("12.00"),
            height=Decimal("12.00"),
            weight=Decimal("1.500"),
        )
        with self.assertRaises(ValidationError):
            duplicate.full_clean()

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                duplicate.save()

    def test_positive_dimension_validation_rejects_zero_and_negative(self):
        """Verifies that length, width, and height must strictly be positive values (> 0)."""
        invalid_cases = [
            {"length": Decimal("0.00")},
            {"length": Decimal("-5.00")},
            {"width": Decimal("0.00")},
            {"width": Decimal("-10.00")},
            {"height": Decimal("0.00")},
            {"height": Decimal("-2.50")},
        ]
        for idx, case in enumerate(invalid_cases):
            params = {
                "sku": f"INVALID-DIM-{idx}",
                "name": "Invalid Dim Product",
                "length": Decimal("10.00"),
                "width": Decimal("10.00"),
                "height": Decimal("10.00"),
                "weight": Decimal("1.000"),
            }
            params.update(case)
            product = Product(**params)

            with self.assertRaises(ValidationError, msg=f"Failed to reject invalid dimension case: {case}"):
                product.full_clean()

            with self.assertRaises(IntegrityError, msg=f"DB constraint failed to reject: {case}"):
                with transaction.atomic():
                    product.save()

    def test_positive_weight_validation_rejects_zero_and_negative(self):
        """Verifies that product mass must strictly be positive (> 0.000 kg)."""
        for weight_val in [Decimal("0.000"), Decimal("-0.750")]:
            product = Product(
                sku=f"INVALID-WT-{weight_val}",
                name="Weight Test Product",
                length=Decimal("10.00"),
                width=Decimal("10.00"),
                height=Decimal("10.00"),
                weight=weight_val,
            )
            with self.assertRaises(ValidationError):
                product.full_clean()

            with self.assertRaises(IntegrityError):
                with transaction.atomic():
                    product.save()


class BoxModelTestCase(TestCase):
    """Automated test cases covering Box entity integrity and constraints."""

    def test_box_creation_with_valid_attributes(self):
        """Verifies shipping box persistence with internal clearances, payload capacity, and cost."""
        box = Box.objects.create(
            name="Heavy Duty Storage Carton",
            internal_length=Decimal("45.00"),
            internal_width=Decimal("35.00"),
            internal_height=Decimal("25.00"),
            max_weight_capacity=Decimal("15.000"),
            packaging_cost=Decimal("3.25"),
            is_active=True,
        )
        self.assertIsNotNone(box.pk)
        self.assertEqual(box.name, "Heavy Duty Storage Carton")
        self.assertEqual(box.internal_volume, Decimal("39375.000"))
        self.assertEqual(box.volume, Decimal("39375.000"))
        self.assertEqual(box.packaging_cost, Decimal("3.25"))
        self.assertTrue(box.is_active)
        self.assertIn("Heavy Duty Storage Carton", str(box))

    def test_positive_internal_dimension_validation_rejects_zero_and_negative(self):
        """Verifies internal clearances must strictly be positive (> 0 cm)."""
        invalid_cases = [
            {"internal_length": Decimal("0.00")},
            {"internal_length": Decimal("-10.00")},
            {"internal_width": Decimal("0.00")},
            {"internal_width": Decimal("-5.00")},
            {"internal_height": Decimal("0.00")},
            {"internal_height": Decimal("-8.00")},
        ]
        for idx, case in enumerate(invalid_cases):
            params = {
                "name": f"Invalid Box Dim {idx}",
                "internal_length": Decimal("20.00"),
                "internal_width": Decimal("20.00"),
                "internal_height": Decimal("20.00"),
                "max_weight_capacity": Decimal("5.000"),
                "packaging_cost": Decimal("1.50"),
            }
            params.update(case)
            box = Box(**params)

            with self.assertRaises(ValidationError, msg=f"Failed to reject invalid box dimension: {case}"):
                box.full_clean()

            with self.assertRaises(IntegrityError, msg=f"DB constraint failed to reject box dimension: {case}"):
                with transaction.atomic():
                    box.save()

    def test_positive_max_weight_capacity_validation(self):
        """Verifies maximum payload capacity must strictly exceed zero (> 0 kg)."""
        for cap in [Decimal("0.000"), Decimal("-15.000")]:
            box = Box(
                name=f"Invalid Cap Box {cap}",
                internal_length=Decimal("20.00"),
                internal_width=Decimal("20.00"),
                internal_height=Decimal("20.00"),
                max_weight_capacity=cap,
                packaging_cost=Decimal("1.50"),
            )
            with self.assertRaises(ValidationError):
                box.full_clean()

            with self.assertRaises(IntegrityError):
                with transaction.atomic():
                    box.save()

    def test_non_negative_box_cost_allows_zero_and_rejects_negative(self):
        """Verifies packaging cost allows 0.00 (promotional packaging) and strictly rejects negative values."""
        # Cost == 0.00 is valid
        free_box = Box.objects.create(
            name="Complimentary Promotional Mailer",
            internal_length=Decimal("20.00"),
            internal_width=Decimal("15.00"),
            internal_height=Decimal("10.00"),
            max_weight_capacity=Decimal("3.000"),
            packaging_cost=Decimal("0.00"),
        )
        self.assertEqual(free_box.packaging_cost, Decimal("0.00"))

        # Cost < 0.00 is strictly invalid
        negative_cost_box = Box(
            name="Negative Cost Container",
            internal_length=Decimal("20.00"),
            internal_width=Decimal("15.00"),
            internal_height=Decimal("10.00"),
            max_weight_capacity=Decimal("3.000"),
            packaging_cost=Decimal("-0.50"),
        )
        with self.assertRaises(ValidationError):
            negative_cost_box.full_clean()

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                negative_cost_box.save()


class OrderItemModelTestCase(TestCase):
    """Automated test cases covering Order and OrderItem constraints."""

    def setUp(self):
        self.order = Order.objects.create(
            order_number="QA-ORD-001",
            customer_reference="QA-CUSTOMER",
        )
        self.product = Product.objects.create(
            sku="QA-ITEM-01",
            name="Packable Widget",
            length=Decimal("10.00"),
            width=Decimal("8.00"),
            height=Decimal("5.00"),
            weight=Decimal("0.450"),
        )

    def test_order_item_creation_with_valid_quantity(self):
        """Verifies OrderItem links Order and Product with positive integer quantity."""
        item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=3,
        )
        self.assertEqual(item.quantity, 3)
        self.assertEqual(item.total_weight, Decimal("1.350"))
        self.assertEqual(item.total_volume, Decimal("1200.000"))

    def test_order_item_positive_quantity_validation_rejects_zero_and_negative(self):
        """Verifies that OrderItem quantity must strictly be >= 1."""
        for qty in [0, -1, -5]:
            item = OrderItem(
                order=self.order,
                product=self.product,
                quantity=qty,
            )
            with self.assertRaises(ValidationError, msg=f"Failed to reject non-positive quantity: {qty}"):
                item.full_clean()

            with self.assertRaises(IntegrityError, msg=f"DB constraint failed to reject non-positive quantity: {qty}"):
                with transaction.atomic():
                    item.save()

    def test_order_item_unique_product_per_order_constraint(self):
        """Verifies that duplicate OrderItem rows for the same product in an order are prevented."""
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=2,
        )
        duplicate_item = OrderItem(
            order=self.order,
            product=self.product,
            quantity=5,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                duplicate_item.save()

