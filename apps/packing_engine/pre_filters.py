from decimal import Decimal
from typing import List, Optional, Tuple
from .dataclasses import BoxDTO, ItemDTO


def validate_box_pre_conditions(
    items: List[ItemDTO],
    box: BoxDTO,
) -> Tuple[bool, Optional[str]]:
    """
    Performs fast O(1) and O(N) pre-checks before executing expensive 3D packing.
    Returns (True, None) if the box is a viable candidate,
    or (False, reason) if mathematically disqualified.
    """
    if not items:
        return True, None

    # 1. Weight capacity check
    total_weight = sum(item.weight for item in items)
    if total_weight > box.max_weight:
        deficit = total_weight - box.max_weight
        return False, (
            f"Total order weight ({total_weight:.3f} kg) exceeds box maximum capacity "
            f"({box.max_weight:.3f} kg) by {deficit:.3f} kg."
        )

    # 2. Volume capacity check
    total_item_volume = sum(item.volume for item in items)
    box_volume = box.volume
    if total_item_volume > box_volume:
        vol_deficit = total_item_volume - box_volume
        return False, (
            f"Total items volume ({total_item_volume:,.1f} cm³) exceeds box internal volume "
            f"({box_volume:,.1f} cm³) by {vol_deficit:,.1f} cm³."
        )

    # 3. Individual dimension compatibility check
    box_sorted = box.sorted_dimensions
    for item in items:
        item_sorted = item.sorted_dimensions
        if not (
            item_sorted[0] <= box_sorted[0]
            and item_sorted[1] <= box_sorted[1]
            and item_sorted[2] <= box_sorted[2]
        ):
            return False, (
                f"Item '{item.sku}' dimensions ({item.length}x{item.width}x{item.height} cm) "
                f"cannot fit inside box '{box.name}' dimensions ({box.length}x{box.width}x{box.height} cm) "
                f"under any rotation."
            )

    return True, None

