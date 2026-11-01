"""
QA Test Suite - Area B: Algorithm Tests
Verifies 3D Extreme Points bin packing heuristic, 6-axis orthogonal rotations,
strict weight constraints, volumetric vs physical feasibility, cost-optimality, and deterministic tie-breaking.
"""
from decimal import Decimal
from django.test import SimpleTestCase
from apps.packing_engine.core import (
    calculate_total_order_weight,
    check_multi_product_spatial_feasibility,
    check_single_product_fit,
    evaluate_box_candidates,
    generate_valid_orientations,
    select_optimal_box,
)
from apps.packing_engine.dataclasses import BoxDTO, ItemDTO


class PackingAlgorithmTestCase(SimpleTestCase):
    """Rigorous algorithmic tests derived from business rules and geometric packing theory."""

    def test_single_product_fits_standard_orientation(self):
        """Verifies that an item whose dimensions align directly with box clearances fits without rotation."""
        item = ItemDTO("I-01", "SKU-01", "Widget", Decimal("10.00"), Decimal("8.00"), Decimal("5.00"), Decimal("0.500"))
        box = BoxDTO(1, "Box 1", Decimal("12.00"), Decimal("10.00"), Decimal("8.00"), Decimal("5.000"), Decimal("1.50"))

        fits, reason = check_single_product_fit(item, box)
        self.assertTrue(fits)
        self.assertIsNone(reason)

        # Test full 3D packing placement
        result = check_multi_product_spatial_feasibility([item], box)
        self.assertTrue(result.is_feasible)
        self.assertEqual(len(result.placed_items), 1)
        placement = result.placed_items[0]
        self.assertEqual((placement.x, placement.y, placement.z), (Decimal("0.00"), Decimal("0.00"), Decimal("0.00")))

    def test_single_product_fits_after_rotation(self):
        """
        Verifies that an item whose base orientation exceeds clearances
        fits when rotated along one of the other 5 orthogonal axes.
        Item: L=30, W=10, H=5 cm. Box: L=12, W=32, H=10 cm.
        Item length (30) > Box length (12), but rotating 90° fits inside Box width (32).
        """
        item = ItemDTO("I-ROT", "SKU-ROT", "Elongated Tool", Decimal("30.00"), Decimal("10.00"), Decimal("5.00"), Decimal("1.000"))
        box = BoxDTO(1, "Rotated Box", Decimal("12.00"), Decimal("32.00"), Decimal("10.00"), Decimal("5.000"), Decimal("2.00"))

        fits, reason = check_single_product_fit(item, box)
        self.assertTrue(fits)
        self.assertIsNone(reason)

        result = check_multi_product_spatial_feasibility([item], box)
        self.assertTrue(result.is_feasible)
        self.assertEqual(len(result.placed_items), 1)

    def test_product_does_not_fit_oversized(self):
        """Verifies that an item with any dimension exceeding all box dimensions is rejected."""
        oversized_item = ItemDTO("I-OVER", "SKU-OVER", "Flagpole", Decimal("55.00"), Decimal("5.00"), Decimal("5.00"), Decimal("1.000"))
        box = BoxDTO(1, "Standard Cube", Decimal("40.00"), Decimal("40.00"), Decimal("40.00"), Decimal("20.000"), Decimal("3.00"))

        fits, reason = check_single_product_fit(oversized_item, box)
        self.assertFalse(fits)
        self.assertIn("exceed box", reason)

        result = check_multi_product_spatial_feasibility([oversized_item], box)
        self.assertFalse(result.is_feasible)
        self.assertIn("exceed box", result.failure_reason)

    def test_multiple_products_fit_together(self):
        """Verifies multi-item packing where items are positioned on distinct extreme points without overlap."""
        items = [
            ItemDTO("I-1", "SKU-A", "Book A", Decimal("15.00"), Decimal("10.00"), Decimal("5.00"), Decimal("0.400")),
            ItemDTO("I-2", "SKU-B", "Book B", Decimal("15.00"), Decimal("10.00"), Decimal("5.00"), Decimal("0.400")),
            ItemDTO("I-3", "SKU-C", "Book C", Decimal("15.00"), Decimal("10.00"), Decimal("5.00"), Decimal("0.400")),
        ]
        # Box accommodates three stacked books (height: 5 * 3 = 15 cm)
        box = BoxDTO(1, "Book Crate", Decimal("20.00"), Decimal("15.00"), Decimal("18.00"), Decimal("5.000"), Decimal("2.00"))

        result = check_multi_product_spatial_feasibility(items, box)
        self.assertTrue(result.is_feasible)
        self.assertEqual(len(result.placed_items), 3)

        # Verify no spatial overlap between any pair of placed items
        placements = result.placed_items
        for i in range(len(placements)):
            for j in range(i + 1, len(placements)):
                p1, p2 = placements[i], placements[j]
                overlap = not (
                    p1.x + p1.dx <= p2.x or p2.x + p2.dx <= p1.x or
                    p1.y + p1.dy <= p2.y or p2.y + p2.dy <= p1.y or
                    p1.z + p1.dz <= p2.z or p2.z + p2.dz <= p1.z
                )
                self.assertFalse(overlap, f"Placements {p1.item_id} and {p2.item_id} spatially collide!")

    def test_multiple_products_cannot_fit_despite_sufficient_total_volume(self):
        """
        Classic 3D bin packing counterexample:
        Box internal cavity: 10 x 10 x 10 cm = 1,000 cm³.
        Three items, each 9 x 9 x 4 cm = 324 cm³.
        Combined item volume: 3 * 324 = 972 cm³ <= 1,000 cm³ (Passes volume pre-filter!).
        However, each item footprint is 9 x 9, requiring stacking.
        Stacking 3 items requires height 3 * 4 = 12 cm > 10 cm.
        The algorithm MUST prove physical infeasibility and reject the box.
        """
        items = [
            ItemDTO("P1", "SKU-PLATE", "Square Plate 1", Decimal("9.00"), Decimal("9.00"), Decimal("4.00"), Decimal("0.300")),
            ItemDTO("P2", "SKU-PLATE", "Square Plate 2", Decimal("9.00"), Decimal("9.00"), Decimal("4.00"), Decimal("0.300")),
            ItemDTO("P3", "SKU-PLATE", "Square Plate 3", Decimal("9.00"), Decimal("9.00"), Decimal("4.00"), Decimal("0.300")),
        ]
        box = BoxDTO(1, "Cube Box 10cm", Decimal("10.00"), Decimal("10.00"), Decimal("10.00"), Decimal("5.000"), Decimal("1.50"))

        total_item_vol = sum(i.length * i.width * i.height for i in items)
        box_vol = box.length * box.width * box.height
        self.assertLess(total_item_vol, box_vol, "Test premise requires total volume <= box volume")

        result = check_multi_product_spatial_feasibility(items, box)
        self.assertFalse(result.is_feasible, "Algorithm must reject physically impossible stacking despite sufficient volume!")

    def test_weight_capacity_exceeded(self):
        """Verifies that a box with insufficient weight capacity is rejected even if items fit spatially."""
        heavy_item = ItemDTO("I-HEAVY", "SKU-LEAD", "Lead Ingot", Decimal("10.00"), Decimal("10.00"), Decimal("5.00"), Decimal("8.500"))
        box = BoxDTO(1, "Small Light Box", Decimal("20.00"), Decimal("20.00"), Decimal("20.00"), Decimal("5.000"), Decimal("1.00"))

        result = check_multi_product_spatial_feasibility([heavy_item], box)
        self.assertFalse(result.is_feasible)
        self.assertIn("exceeds box maximum capacity", result.failure_reason)

    def test_quantity_correctly_affects_total_weight(self):
        """Verifies that item quantities scale the total order weight proportionally."""
        items = [
            ItemDTO("I-1", "SKU-A", "Widget", Decimal("10.00"), Decimal("5.00"), Decimal("5.00"), Decimal("0.750")),
            ItemDTO("I-2", "SKU-A", "Widget", Decimal("10.00"), Decimal("5.00"), Decimal("5.00"), Decimal("0.750")),
            ItemDTO("I-3", "SKU-A", "Widget", Decimal("10.00"), Decimal("5.00"), Decimal("5.00"), Decimal("0.750")),
            ItemDTO("I-4", "SKU-A", "Widget", Decimal("10.00"), Decimal("5.00"), Decimal("5.00"), Decimal("0.750")),
        ]
        total_weight = calculate_total_order_weight(items)
        self.assertEqual(total_weight, Decimal("3.000"))

        # Box capacity 2.5 kg must reject
        box_under = BoxDTO(1, "Box Under", Decimal("30.00"), Decimal("30.00"), Decimal("30.00"), Decimal("2.500"), Decimal("1.50"))
        res_under = check_multi_product_spatial_feasibility(items, box_under)
        self.assertFalse(res_under.is_feasible)

        # Box capacity 5.0 kg must accept
        box_over = BoxDTO(2, "Box Over", Decimal("30.00"), Decimal("30.00"), Decimal("30.00"), Decimal("5.000"), Decimal("2.50"))
        res_over = check_multi_product_spatial_feasibility(items, box_over)
        self.assertTrue(res_over.is_feasible)

    def test_lowest_cost_feasible_box_selected(self):
        """Verifies that the algorithm selects the lowest packaging cost among all feasible candidates."""
        items = [ItemDTO("I-1", "SKU-1", "Item", Decimal("10.00"), Decimal("10.00"), Decimal("10.00"), Decimal("1.000"))]
        box_expensive = BoxDTO(1, "Expensive Box", Decimal("30.00"), Decimal("30.00"), Decimal("30.00"), Decimal("10.000"), Decimal("4.50"))
        box_cheap = BoxDTO(2, "Economy Box", Decimal("20.00"), Decimal("20.00"), Decimal("20.00"), Decimal("5.000"), Decimal("1.25"))

        winning_result, summaries = select_optimal_box(items, [box_expensive, box_cheap])
        self.assertIsNotNone(winning_result)
        self.assertTrue(winning_result.is_feasible)
        self.assertEqual(winning_result.box.box_id, box_cheap.box_id)
        self.assertEqual(winning_result.box.packaging_cost, Decimal("1.25"))

    def test_inactive_boxes_ignored(self):
        """Verifies that deactivated candidate boxes are never evaluated or selected."""
        items = [ItemDTO("I-1", "SKU-1", "Item", Decimal("10.00"), Decimal("10.00"), Decimal("10.00"), Decimal("1.000"))]
        active_box = BoxDTO(1, "Active Box", Decimal("20.00"), Decimal("20.00"), Decimal("20.00"), Decimal("5.000"), Decimal("3.00"), is_active=True)
        inactive_cheap_box = BoxDTO(2, "Inactive Cheap Box", Decimal("20.00"), Decimal("20.00"), Decimal("20.00"), Decimal("5.000"), Decimal("1.00"), is_active=False)

        winning_result, summaries = select_optimal_box(items, [inactive_cheap_box, active_box])
        self.assertEqual(winning_result.box.name, "Active Box")

    def test_no_feasible_box_returns_infeasible_with_reasons(self):
        """Verifies that when no candidate can fit the order, is_feasible is False with descriptive reasons."""
        giant_item = ItemDTO("I-GIANT", "SKU-GIANT", "Generator", Decimal("100.00"), Decimal("100.00"), Decimal("100.00"), Decimal("50.000"))
        small_box = BoxDTO(1, "Small Mailer", Decimal("20.00"), Decimal("15.00"), Decimal("10.00"), Decimal("2.000"), Decimal("1.00"))

        winning_result, summaries = select_optimal_box([giant_item], [small_box])
        self.assertFalse(winning_result.is_feasible)
        self.assertIsNone(winning_result.box)
        self.assertEqual(len(summaries), 1)
        self.assertFalse(summaries[0].is_feasible)
        self.assertIn("exceeds box maximum capacity", summaries[0].rejection_reason)

    def test_empty_order_handling(self):
        """Verifies that an empty item list returns total weight 0 and handles empty evaluation safely."""
        self.assertEqual(calculate_total_order_weight([]), Decimal("0.000"))
        box = BoxDTO(1, "Standard Box", Decimal("20.00"), Decimal("20.00"), Decimal("20.00"), Decimal("5.000"), Decimal("1.50"))
        res, _ = select_optimal_box([], [box])
        self.assertFalse(res.is_feasible)
        self.assertIn("no items", res.failure_reason)

    def test_boundary_dimension_conditions_exact_fit(self):
        """
        Boundary condition: Item dimensions exactly equal box internal clearances.
        Item: 20.00 x 15.00 x 10.00 cm. Box: 20.00 x 15.00 x 10.00 cm.
        Must fit perfectly with 100.0% volume utilization.
        """
        item = ItemDTO("I-EXACT", "SKU-EXACT", "Exact Fit Block", Decimal("20.00"), Decimal("15.00"), Decimal("10.00"), Decimal("1.000"))
        box = BoxDTO(1, "Exact Fit Container", Decimal("20.00"), Decimal("15.00"), Decimal("10.00"), Decimal("5.000"), Decimal("2.00"))

        result = check_multi_product_spatial_feasibility([item], box)
        self.assertTrue(result.is_feasible)
        self.assertEqual(result.volume_utilization_pct, Decimal("100.00"))
        placement = result.placed_items[0]
        self.assertEqual((placement.x, placement.y, placement.z), (Decimal("0.00"), Decimal("0.00"), Decimal("0.00")))
        self.assertEqual((placement.dx, placement.dy, placement.dz), (Decimal("20.00"), Decimal("15.00"), Decimal("10.00")))

    def test_deterministic_tie_breaking(self):
        """
        Deterministic tie-breaking:
        When multiple candidate boxes have identical cost ($2.00), the tie is deterministically broken by:
        1. Smaller volume (tighter cavity)
        2. Smaller weight limit (better capacity matching)
        3. Alphabetical box name
        """
        item = ItemDTO("I-1", "SKU-1", "Gadget", Decimal("10.00"), Decimal("10.00"), Decimal("10.00"), Decimal("1.000"))
        box_large_vol = BoxDTO(1, "Box Large Volume", Decimal("30.00"), Decimal("30.00"), Decimal("30.00"), Decimal("10.000"), Decimal("2.00"))
        box_small_vol = BoxDTO(2, "Box Small Volume", Decimal("15.00"), Decimal("15.00"), Decimal("15.00"), Decimal("10.000"), Decimal("2.00"))

        # Both orderings must deterministically select box_small_vol
        result1, _ = select_optimal_box([item], [box_large_vol, box_small_vol])
        result2, _ = select_optimal_box([item], [box_small_vol, box_large_vol])

        self.assertEqual(result1.box.box_id, box_small_vol.box_id)
        self.assertEqual(result2.box.box_id, box_small_vol.box_id)
        self.assertEqual(result1.box.name, "Box Small Volume")

