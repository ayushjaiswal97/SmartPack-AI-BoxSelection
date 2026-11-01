from decimal import Decimal
import pytest
from apps.packing_engine.core import (
    calculate_total_order_weight,
    generate_valid_orientations,
    check_single_product_fit,
    check_multi_product_spatial_feasibility,
    evaluate_box_candidates,
    select_optimal_box,
)
from apps.packing_engine.dataclasses import BoxDTO, ItemDTO


# ============================================================================
# 1. Total Order Weight Tests
# ============================================================================

def test_calculate_total_order_weight_empty():
    assert calculate_total_order_weight([]) == Decimal("0.000")


def test_calculate_total_order_weight_multiple_items():
    items = [
        ItemDTO("1", "SKU-A", "Item A", Decimal("10"), Decimal("10"), Decimal("10"), Decimal("0.250")),
        ItemDTO("2", "SKU-B", "Item B", Decimal("10"), Decimal("10"), Decimal("10"), Decimal("1.755")),
        ItemDTO("3", "SKU-C", "Item C", Decimal("10"), Decimal("10"), Decimal("10"), Decimal("0.495")),
    ]
    # Exact decimal sum: 0.250 + 1.755 + 0.495 = 2.500
    total = calculate_total_order_weight(items)
    assert total == Decimal("2.500")
    assert isinstance(total, Decimal)


# ============================================================================
# 2. Orientation Generation Tests
# ============================================================================

def test_generate_valid_orientations_cuboid():
    """General cuboid with 3 distinct sides has 6 unique orthogonal orientations."""
    rotations = generate_valid_orientations(Decimal("10"), Decimal("15"), Decimal("20"))
    assert len(rotations) == 6
    assert (Decimal("10"), Decimal("15"), Decimal("20")) in rotations
    assert (Decimal("20"), Decimal("15"), Decimal("10")) in rotations


def test_generate_valid_orientations_cube_deduplication():
    """Cube has identical sides, resulting in 1 unique orientation."""
    rotations = generate_valid_orientations(Decimal("10"), Decimal("10"), Decimal("10"))
    assert len(rotations) == 1
    assert rotations[0] == (Decimal("10"), Decimal("10"), Decimal("10"))


def test_generate_valid_orientations_square_prism():
    """Square prism (two equal sides) has 3 unique orientations."""
    rotations = generate_valid_orientations(Decimal("10"), Decimal("10"), Decimal("25"))
    assert len(rotations) == 3


# ============================================================================
# 3. Single-Product Fit Tests
# ============================================================================

def test_check_single_product_fit_successful_rotation():
    """Item dimensions (30 x 10 x 5) fit inside box (15 x 35 x 10) only when rotated."""
    item = ItemDTO("1", "SKU-ROT", "Rotatable Product", Decimal("30"), Decimal("10"), Decimal("5"), Decimal("1.000"))
    box = BoxDTO(1, "Box A", Decimal("15"), Decimal("35"), Decimal("10"), Decimal("5.000"), Decimal("2.00"))
    
    fits, reason = check_single_product_fit(item, box)
    assert fits is True
    assert reason is None


def test_check_single_product_fit_dimensional_exceeded():
    """Item length 40 exceeds all box clearances (max 30)."""
    item = ItemDTO("1", "SKU-LONG", "Long Item", Decimal("40"), Decimal("5"), Decimal("5"), Decimal("1.000"))
    box = BoxDTO(1, "Box Small", Decimal("30"), Decimal("20"), Decimal("10"), Decimal("5.000"), Decimal("2.00"))

    fits, reason = check_single_product_fit(item, box)
    assert fits is False
    assert "exceed box" in reason


def test_check_single_product_fit_weight_exceeded():
    """Item weight exceeds box weight capacity."""
    item = ItemDTO("1", "SKU-HVY", "Heavy Item", Decimal("10"), Decimal("10"), Decimal("10"), Decimal("12.000"))
    box = BoxDTO(1, "Light Box", Decimal("20"), Decimal("20"), Decimal("20"), Decimal("10.000"), Decimal("2.00"))

    fits, reason = check_single_product_fit(item, box)
    assert fits is False
    assert "exceeds box maximum weight capacity" in reason


# ============================================================================
# 4. Multi-Product 3D Spatial Feasibility Tests
# ============================================================================

def test_volume_fits_but_spatial_packing_impossible_counterexample():
    """
    CRUCIAL PROOF: Proves that checking combined volume is NOT sufficient.
    
    Box: 10 x 10 x 10 cm -> Volume = 1000 cm³.
    3 Items, each 9 x 9 x 4 cm -> Volume = 324 cm³ each.
    Total Volume = 3 x 324 = 972 cm³ <= 1000 cm³ (Volume check alone PASSES).
    
    However:
      - Footprint is 9x9 cm. Cannot place side-by-side (9 + 9 = 18 > 10 cm).
      - Rotating to 9x4x9 cm: two items along height require 9 + 9 = 18 > 10 cm.
      - Therefore, items can only be stacked vertically with height 4.
      - 3 items stacked vertically require 4 + 4 + 4 = 12 cm > 10 cm box height!
    
    Expected Result: Algorithm MUST reject the box due to spatial impossibility!
    """
    box = BoxDTO(1, "Cube Box", Decimal("10"), Decimal("10"), Decimal("10"), Decimal("10.000"), Decimal("1.50"))
    items = [
        ItemDTO("1", "SKU-FLAT-1", "Flat Square 1", Decimal("9"), Decimal("9"), Decimal("4"), Decimal("0.500")),
        ItemDTO("2", "SKU-FLAT-2", "Flat Square 2", Decimal("9"), Decimal("9"), Decimal("4"), Decimal("0.500")),
        ItemDTO("3", "SKU-FLAT-3", "Flat Square 3", Decimal("9"), Decimal("9"), Decimal("4"), Decimal("0.500")),
    ]

    # Verify our premise: combined volume strictly fits within box volume
    assert sum(it.volume for it in items) == Decimal("972")
    assert box.volume == Decimal("1000")
    assert sum(it.volume for it in items) < box.volume

    # Run spatial packing
    result = check_multi_product_spatial_feasibility(items, box)
    assert result.is_feasible is False
    assert "cannot be placed inside box" in result.failure_reason


def test_multi_product_successful_spatial_packing():
    """Multiple items packed tightly without overlapping."""
    box = BoxDTO(1, "Standard Box", Decimal("20"), Decimal("15"), Decimal("10"), Decimal("5.000"), Decimal("2.00"))
    items = [
        ItemDTO("1", "SKU-BOOK", "Textbook", Decimal("15"), Decimal("10"), Decimal("4"), Decimal("0.800")),
        ItemDTO("2", "SKU-AUD", "Headphones", Decimal("12"), Decimal("8"), Decimal("5"), Decimal("0.400")),
    ]

    result = check_multi_product_spatial_feasibility(items, box)
    assert result.is_feasible is True
    assert len(result.placed_items) == 2

    # Verify non-overlap
    p1, p2 = result.placed_items[0], result.placed_items[1]
    overlap = (
        p1.x < p2.x + p2.dx and p1.x + p1.dx > p2.x
        and p1.y < p2.y + p2.dy and p1.y + p1.dy > p2.y
        and p1.z < p2.z + p2.dz and p1.z + p1.dz > p2.z
    )
    assert not overlap


# ============================================================================
# 5. Candidate Evaluation & Optimal Selection Tests
# ============================================================================

def test_evaluate_box_candidates_inactive_box():
    """Inactive box is audited with inactive rejection reason."""
    items = [ItemDTO("1", "SKU-1", "Product", Decimal("5"), Decimal("5"), Decimal("5"), Decimal("0.500"))]
    inactive_box = BoxDTO(1, "Inactive Box", Decimal("20"), Decimal("20"), Decimal("20"), Decimal("10"), Decimal("1.00"), is_active=False)

    summaries = evaluate_box_candidates(items, [inactive_box])
    assert len(summaries) == 1
    assert summaries[0].is_feasible is False
    assert "marked as inactive" in summaries[0].rejection_reason


def test_select_optimal_box_lowest_cost():
    """System selects the cheapest feasible box among candidates."""
    items = [ItemDTO("1", "SKU-1", "Product", Decimal("10"), Decimal("10"), Decimal("10"), Decimal("1.000"))]
    box_cheap = BoxDTO(1, "Cheap Box", Decimal("15"), Decimal("15"), Decimal("15"), Decimal("5"), Decimal("1.50"))
    box_expensive = BoxDTO(2, "Expensive Box", Decimal("30"), Decimal("30"), Decimal("30"), Decimal("15"), Decimal("6.00"))

    winning_result, summaries = select_optimal_box(items, [box_expensive, box_cheap])
    assert winning_result.is_feasible is True
    assert winning_result.box.box_id == 1
    assert winning_result.box.packaging_cost == Decimal("1.50")


def test_select_optimal_box_deterministic_tie_breaking():
    """
    Tie-breaking hierarchy:
    When packaging costs are identical (₹2.50), the box with smaller volume is selected
    to minimize void fill and dimensional courier charges.
    """
    items = [ItemDTO("1", "SKU-1", "Small Product", Decimal("5"), Decimal("5"), Decimal("5"), Decimal("0.200"))]
    # Box A: 15x15x15 = 3375 cm³, Cost ₹2.50
    box_smaller = BoxDTO(1, "Smaller Box", Decimal("15"), Decimal("15"), Decimal("15"), Decimal("10"), Decimal("2.50"))
    # Box B: 25x25x25 = 15625 cm³, Cost ₹2.50
    box_larger = BoxDTO(2, "Larger Box", Decimal("25"), Decimal("25"), Decimal("25"), Decimal("10"), Decimal("2.50"))

    winning_result, _ = select_optimal_box(items, [box_larger, box_smaller])
    assert winning_result.is_feasible is True
    assert winning_result.box.box_id == 1  # Picks smaller volume

