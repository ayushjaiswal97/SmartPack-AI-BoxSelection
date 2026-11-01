from decimal import Decimal
import pytest
from apps.packing_engine.algorithms.extreme_points import ExtremePointsPacker
from apps.packing_engine.dataclasses import BoxDTO, ItemDTO
from apps.packing_engine.pre_filters import validate_box_pre_conditions
from apps.packing_engine.rotations import get_orthogonal_rotations
from apps.packing_engine.selector import BoxSelectorService


def test_rotations_cube_deduplication():
    """A cube (all sides equal) has only 1 unique orthogonal orientation."""
    rotations = get_orthogonal_rotations(Decimal("10"), Decimal("10"), Decimal("10"))
    assert len(rotations) == 1
    assert rotations[0] == (Decimal("10"), Decimal("10"), Decimal("10"))


def test_rotations_square_prism_deduplication():
    """A square prism (two sides equal) has exactly 3 unique orthogonal orientations."""
    rotations = get_orthogonal_rotations(Decimal("10"), Decimal("10"), Decimal("20"))
    assert len(rotations) == 3
    assert (Decimal("10"), Decimal("10"), Decimal("20")) in rotations
    assert (Decimal("10"), Decimal("20"), Decimal("10")) in rotations
    assert (Decimal("20"), Decimal("10"), Decimal("10")) in rotations


def test_rotations_general_cuboid():
    """A cuboid with distinct dimensions has exactly 6 unique orientations."""
    rotations = get_orthogonal_rotations(Decimal("10"), Decimal("15"), Decimal("20"))
    assert len(rotations) == 6


def test_rotations_upright_constraint():
    """When allow_upright_only is True, height axis cannot be tilted."""
    rotations = get_orthogonal_rotations(
        Decimal("10"), Decimal("15"), Decimal("20"), allow_upright_only=True
    )
    assert len(rotations) == 2
    for r in rotations:
        assert r[2] == Decimal("20")  # Height remains Z


def test_pre_filter_weight_capacity_exceeded():
    """Reject boxes when total weight exceeds capacity."""
    items = [
        ItemDTO("1", "SKU-1", "Heavy Item", Decimal("10"), Decimal("10"), Decimal("10"), Decimal("6.000")),
    ]
    box = BoxDTO(1, "Light Box", Decimal("20"), Decimal("20"), Decimal("20"), Decimal("5.000"), Decimal("2.00"))
    
    is_valid, reason = validate_box_pre_conditions(items, box)
    assert not is_valid
    assert "exceeds box maximum capacity" in reason


def test_pre_filter_volume_exceeded():
    """Reject boxes when total item volume exceeds internal box volume."""
    items = [
        ItemDTO("1", "SKU-1", "Large Item", Decimal("10"), Decimal("10"), Decimal("10"), Decimal("1.000")),
    ]
    box = BoxDTO(1, "Tiny Box", Decimal("8"), Decimal("8"), Decimal("8"), Decimal("5.000"), Decimal("2.00"))
    
    is_valid, reason = validate_box_pre_conditions(items, box)
    assert not is_valid
    assert "exceeds box internal volume" in reason


def test_pre_filter_dimension_exceeded():
    """Reject boxes when an item cannot fit under any rotation."""
    # Item is 25 cm long, box max dimension is 20 cm
    items = [
        ItemDTO("1", "SKU-ROD", "Long Rod", Decimal("25"), Decimal("5"), Decimal("5"), Decimal("0.500")),
    ]
    box = BoxDTO(1, "Cube Box", Decimal("20"), Decimal("20"), Decimal("20"), Decimal("5.000"), Decimal("2.00"))
    
    is_valid, reason = validate_box_pre_conditions(items, box)
    assert not is_valid
    assert "cannot fit inside box" in reason


def test_rotational_packing_success():
    """
    Item of size (30 x 10 x 5) placed into box (15 x 35 x 10).
    In default orientation (L=30, W=10), L=30 exceeds box length 15.
    Must rotate to (10 x 30 x 5) to fit inside (15 x 35 x 10).
    """
    item = ItemDTO("1", "SKU-ROTATE", "Rotatable Product", Decimal("30"), Decimal("10"), Decimal("5"), Decimal("1.000"))
    box = BoxDTO(1, "Rotated Box", Decimal("15"), Decimal("35"), Decimal("10"), Decimal("5.000"), Decimal("2.00"))
    
    packer = ExtremePointsPacker()
    result = packer.pack([item], box)
    
    assert result.is_feasible is True
    assert len(result.placed_items) == 1
    placement = result.placed_items[0]
    # Check that rotated item stays within box dimensions
    assert placement.x + placement.dx <= box.length
    assert placement.y + placement.dy <= box.width
    assert placement.z + placement.dz <= box.height


def test_multi_item_packing_non_overlapping():
    """Pack multiple items and verify that no placed items collide."""
    items = [
        ItemDTO("1", "SKU-A", "Item A", Decimal("10"), Decimal("10"), Decimal("10"), Decimal("0.500")),
        ItemDTO("2", "SKU-B", "Item B", Decimal("10"), Decimal("10"), Decimal("10"), Decimal("0.500")),
        ItemDTO("3", "SKU-C", "Item C", Decimal("10"), Decimal("10"), Decimal("10"), Decimal("0.500")),
    ]
    box = BoxDTO(1, "Medium Box", Decimal("25"), Decimal("20"), Decimal("15"), Decimal("5.000"), Decimal("3.00"))
    
    packer = ExtremePointsPacker()
    result = packer.pack(items, box)
    
    assert result.is_feasible is True
    assert len(result.placed_items) == 3

    # Pairwise collision verification
    placements = result.placed_items
    for i in range(len(placements)):
        for j in range(i + 1, len(placements)):
            p1, p2 = placements[i], placements[j]
            overlap = (
                p1.x < p2.x + p2.dx and p1.x + p1.dx > p2.x
                and p1.y < p2.y + p2.dy and p1.y + p1.dy > p2.y
                and p1.z < p2.z + p2.dz and p1.z + p1.dz > p2.z
            )
            assert not overlap, f"Collision detected between {p1.sku} and {p2.sku}!"


def test_box_selector_recommends_lowest_cost():
    """Given multiple feasible boxes, selector must pick the one with lowest cost."""
    items = [
        ItemDTO("1", "SKU-1", "Product", Decimal("10"), Decimal("10"), Decimal("10"), Decimal("1.000")),
    ]
    box_expensive = BoxDTO(1, "Box Expensive", Decimal("30"), Decimal("30"), Decimal("30"), Decimal("10"), Decimal("8.50"))
    box_cheapest = BoxDTO(2, "Box Cheapest", Decimal("15"), Decimal("15"), Decimal("15"), Decimal("5"), Decimal("2.10"))
    box_mid = BoxDTO(3, "Box Mid", Decimal("20"), Decimal("20"), Decimal("20"), Decimal("8"), Decimal("4.20"))

    selector = BoxSelectorService()
    result, log = selector.select_best_box(items, [box_expensive, box_cheapest, box_mid])

    assert result.is_feasible is True
    assert result.box is not None
    assert result.box.box_id == 2
    assert result.box.packaging_cost == Decimal("2.10")


def test_box_selector_tie_breaking_by_volume():
    """When costs are tied, selector chooses the box with smaller internal volume."""
    items = [
        ItemDTO("1", "SKU-1", "Product", Decimal("10"), Decimal("10"), Decimal("10"), Decimal("1.000")),
    ]
    # Box A: 20x20x20 = 8000 cm³, cost 3.00
    box_large = BoxDTO(1, "Box Large", Decimal("20"), Decimal("20"), Decimal("20"), Decimal("10"), Decimal("3.00"))
    # Box B: 15x15x15 = 3375 cm³, cost 3.00
    box_compact = BoxDTO(2, "Box Compact", Decimal("15"), Decimal("15"), Decimal("15"), Decimal("10"), Decimal("3.00"))

    selector = BoxSelectorService()
    result, _ = selector.select_best_box(items, [box_large, box_compact])

    assert result.is_feasible is True
    assert result.box.box_id == 2  # Chooses compact box to minimize void fill

