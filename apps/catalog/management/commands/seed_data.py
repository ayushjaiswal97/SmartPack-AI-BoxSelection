from decimal import Decimal
from django.core.management.base import BaseCommand
from apps.catalog.models import Product, ShippingBox


class Command(BaseCommand):
    help = "Seed database with realistic ecommerce products and warehouse shipping boxes."

    def handle(self, *args, **options):
        self.stdout.write("Seeding catalog data...")

        # 1. Shipping Boxes
        boxes = [
            {
                "name": "Small Mailer Box (BX-SM)",
                "internal_length": Decimal("22.00"),
                "internal_width": Decimal("16.00"),
                "internal_height": Decimal("10.00"),
                "max_weight_capacity": Decimal("2.500"),
                "packaging_cost": Decimal("1.20"),
            },
            {
                "name": "Medium Standard Box (BX-MD)",
                "internal_length": Decimal("35.00"),
                "internal_width": Decimal("25.00"),
                "internal_height": Decimal("15.00"),
                "max_weight_capacity": Decimal("5.000"),
                "packaging_cost": Decimal("2.10"),
            },
            {
                "name": "Medium Deep Box (BX-MD-DP)",
                "internal_length": Decimal("35.00"),
                "internal_width": Decimal("25.00"),
                "internal_height": Decimal("28.00"),
                "max_weight_capacity": Decimal("8.000"),
                "packaging_cost": Decimal("2.85"),
            },
            {
                "name": "Large Standard Box (BX-LG)",
                "internal_length": Decimal("50.00"),
                "internal_width": Decimal("35.00"),
                "internal_height": Decimal("25.00"),
                "max_weight_capacity": Decimal("12.000"),
                "packaging_cost": Decimal("4.50"),
            },
            {
                "name": "Heavy Duty Long Box (BX-LNG)",
                "internal_length": Decimal("75.00"),
                "internal_width": Decimal("25.00"),
                "internal_height": Decimal("20.00"),
                "max_weight_capacity": Decimal("15.000"),
                "packaging_cost": Decimal("5.20"),
            },
            {
                "name": "Extra Large Warehouse Box (BX-XL)",
                "internal_length": Decimal("70.00"),
                "internal_width": Decimal("50.00"),
                "internal_height": Decimal("40.00"),
                "max_weight_capacity": Decimal("25.000"),
                "packaging_cost": Decimal("7.50"),
            },
        ]

        for box_data in boxes:
            box, created = ShippingBox.objects.update_or_create(
                name=box_data["name"],
                defaults=box_data,
            )
            action = "Created" if created else "Updated"
            self.stdout.write(f"  {action} Box: {box.name}")

        # 2. Products
        products = [
            {
                "sku": "ELEC-PHN-01",
                "name": "Smartphone Pro 6.7-inch",
                "length": Decimal("16.00"),
                "width": Decimal("8.00"),
                "height": Decimal("2.00"),
                "weight": Decimal("0.250"),
            },
            {
                "sku": "ELEC-AUD-02",
                "name": "Wireless Noise-Cancelling Headphones",
                "length": Decimal("20.00"),
                "width": Decimal("18.00"),
                "height": Decimal("8.00"),
                "weight": Decimal("0.400"),
            },
            {
                "sku": "APP-SHOE-03",
                "name": "Men's Performance Running Shoes",
                "length": Decimal("32.00"),
                "width": Decimal("20.00"),
                "height": Decimal("12.00"),
                "weight": Decimal("0.950"),
            },
            {
                "sku": "MED-BOK-04",
                "name": "Hardcover Architecture Textbook",
                "length": Decimal("24.00"),
                "width": Decimal("17.00"),
                "height": Decimal("4.00"),
                "weight": Decimal("0.800"),
            },
            {
                "sku": "ELEC-KEY-05",
                "name": "Full-Size Mechanical Gaming Keyboard",
                "length": Decimal("45.00"),
                "width": Decimal("15.00"),
                "height": Decimal("4.50"),
                "weight": Decimal("1.200"),
            },
            {
                "sku": "HOME-MUG-06",
                "name": "Ceramic Coffee Mug (Boxed)",
                "length": Decimal("12.00"),
                "width": Decimal("10.00"),
                "height": Decimal("11.00"),
                "weight": Decimal("0.380"),
            },
            {
                "sku": "SPO-MAT-07",
                "name": "Eco-Friendly Yoga Mat (Rolled)",
                "length": Decimal("65.00"),
                "width": Decimal("14.00"),
                "height": Decimal("14.00"),
                "weight": Decimal("1.100"),
            },
            {
                "sku": "HOME-BOT-08",
                "name": "Insulated Stainless Steel Water Bottle 1L",
                "length": Decimal("27.00"),
                "width": Decimal("8.00"),
                "height": Decimal("8.00"),
                "weight": Decimal("0.450"),
            },
            {
                "sku": "ELEC-MON-09",
                "name": "Ultra-Slim 24-inch Desktop Monitor",
                "length": Decimal("55.00"),
                "width": Decimal("38.00"),
                "height": Decimal("14.00"),
                "weight": Decimal("4.200"),
            },
            {
                "sku": "FIT-DUM-10",
                "name": "Cast Iron Hex Dumbbell (5 kg)",
                "length": Decimal("28.00"),
                "width": Decimal("12.00"),
                "height": Decimal("12.00"),
                "weight": Decimal("5.000"),
            },
        ]

        for prod_data in products:
            prod, created = Product.objects.update_or_create(
                sku=prod_data["sku"],
                defaults=prod_data,
            )
            action = "Created" if created else "Updated"
            self.stdout.write(f"  {action} Product: {prod.sku} ({prod.name})")

        self.stdout.write(self.style.SUCCESS("Successfully seeded catalog data."))

