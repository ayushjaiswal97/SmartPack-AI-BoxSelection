import time
from decimal import Decimal
from typing import List, Tuple
from ..dataclasses import BoxDTO, ItemDTO, PlacementDTO, PackingResultDTO
from ..pre_filters import validate_box_pre_conditions
from ..rotations import get_orthogonal_rotations


def _check_overlap(
    p1_x: Decimal, p1_y: Decimal, p1_z: Decimal,
    d1_x: Decimal, d1_y: Decimal, d1_z: Decimal,
    p2_x: Decimal, p2_y: Decimal, p2_z: Decimal,
    d2_x: Decimal, d2_y: Decimal, d2_z: Decimal,
) -> bool:
    """Returns True if the two 3D boxes intersect/overlap in open volume."""
    return (
        p1_x < p2_x + d2_x and p1_x + d1_x > p2_x
        and p1_y < p2_y + d2_y and p1_y + d1_y > p2_y
        and p1_z < p2_z + d2_z and p1_z + d1_z > p2_z
    )


def _point_is_inside_box(
    px: Decimal, py: Decimal, pz: Decimal,
    bx: Decimal, by: Decimal, bz: Decimal,
    bdx: Decimal, bdy: Decimal, bdz: Decimal,
) -> bool:
    """Returns True if point (px, py, pz) is strictly inside a placed box."""
    return (
        bx <= px < bx + bdx
        and by <= py < by + bdy
        and bz <= pz < bz + bdz
    )


class ExtremePointsPacker:
    """
    3D Bin Packing implementation using the Extreme Points (EP) Heuristic
    with 6-axis orthogonal rotation support and Best-Fit Decreasing ordering.
    """

    def __init__(self, allow_upright_only: bool = False):
        self.allow_upright_only = allow_upright_only

    def pack(self, items: List[ItemDTO], box: BoxDTO) -> PackingResultDTO:
        start_time = time.perf_counter()

        # Step 1: Run O(1) / O(N) pre-filters (Weight, Volume, Outer Dimensions)
        is_viable, rejection_reason = validate_box_pre_conditions(items, box)
        if not is_viable:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            return PackingResultDTO(
                is_feasible=False,
                box=box,
                unplaced_items=list(items),
                failure_reason=rejection_reason or "Pre-filter condition failed.",
                execution_time_ms=elapsed_ms,
            )

        if not items:
            return PackingResultDTO(
                is_feasible=True,
                box=box,
                placed_items=[],
                unplaced_items=[],
                volume_utilization_pct=Decimal("0.00"),
                weight_utilization_pct=Decimal("0.00"),
                execution_time_ms=0,
            )

        # Step 2: Sort items by Best-Fit Decreasing (BFD)
        # Primary: Volume descending; Secondary: Max single dimension descending
        sorted_items = sorted(
            items,
            key=lambda it: (it.volume, max(it.length, it.width, it.height)),
            reverse=True,
        )

        # Step 3: Extreme Points initialization
        # Candidate points are represented as (x, y, z)
        extreme_points: List[Tuple[Decimal, Decimal, Decimal]] = [
            (Decimal("0.00"), Decimal("0.00"), Decimal("0.00"))
        ]
        placements: List[PlacementDTO] = []
        unplaced: List[ItemDTO] = []

        box_l = box.length
        box_w = box.width
        box_h = box.height

        for item in sorted_items:
            rotations = get_orthogonal_rotations(
                item.length,
                item.width,
                item.height,
                allow_upright_only=self.allow_upright_only,
            )

            placed = False

            # Candidate points prioritized by Z (bottom first), then Y, then X
            for pt in list(extreme_points):
                px, py, pz = pt

                for dx, dy, dz in rotations:
                    # Boundary check against box internal walls
                    if px + dx > box_l or py + dy > box_w or pz + dz > box_h:
                        continue

                    # Collision check with already placed items
                    has_collision = False
                    for p in placements:
                        if _check_overlap(
                            px, py, pz, dx, dy, dz,
                            p.x, p.y, p.z, p.dx, p.dy, p.dz,
                        ):
                            has_collision = True
                            break

                    if not has_collision:
                        # Valid placement found!
                        placement = PlacementDTO(
                            item_id=item.item_id,
                            sku=item.sku,
                            name=item.name,
                            x=px,
                            y=py,
                            z=pz,
                            dx=dx,
                            dy=dy,
                            dz=dz,
                        )
                        placements.append(placement)
                        placed = True

                        # Generate new extreme points from this placement
                        new_points = [
                            (px + dx, py, pz),
                            (px, py + dy, pz),
                            (px, py, pz + dz),
                        ]

                        # Project onto edges of existing items to catch tight crevices
                        for ex_p in placements:
                            if ex_p.x + ex_p.dx > px and ex_p.x + ex_p.dx <= box_l:
                                new_points.append((ex_p.x + ex_p.dx, py, pz))
                            if ex_p.y + ex_p.dy > py and ex_p.y + ex_p.dy <= box_w:
                                new_points.append((px, ex_p.y + ex_p.dy, pz))
                            if ex_p.z + ex_p.dz > pz and ex_p.z + ex_p.dz <= box_h:
                                new_points.append((px, py, ex_p.z + ex_p.dz))

                        # Filter valid extreme points:
                        # 1. Must be within box bounds
                        # 2. Must not be inside any placed item
                        filtered_points = []
                        all_points = set(extreme_points + new_points)

                        for cand_x, cand_y, cand_z in all_points:
                            if cand_x >= box_l or cand_y >= box_w or cand_z >= box_h:
                                continue

                            inside = False
                            for pl in placements:
                                if _point_is_inside_box(
                                    cand_x, cand_y, cand_z,
                                    pl.x, pl.y, pl.z, pl.dx, pl.dy, pl.dz,
                                ):
                                    inside = True
                                    break

                            if not inside:
                                filtered_points.append((cand_x, cand_y, cand_z))

                        # Sort candidate points: Z ascending (lowest first), Y asc, X asc
                        filtered_points.sort(key=lambda p: (p[2], p[1], p[0]))
                        extreme_points = filtered_points
                        break  # Break out of rotations loop

                if placed:
                    break  # Break out of points loop

            if not placed:
                unplaced.append(item)
                # Early failure: if an item cannot be placed, this box cannot fit the order
                break

        elapsed_ms = max(1, int((time.perf_counter() - start_time) * 1000))

        if unplaced:
            failed_item = unplaced[0]
            return PackingResultDTO(
                is_feasible=False,
                box=box,
                placed_items=placements,
                unplaced_items=unplaced,
                failure_reason=(
                    f"Spatial collision constraint: Item '{failed_item.sku}' "
                    f"({failed_item.length}x{failed_item.width}x{failed_item.height} cm) "
                    f"cannot be packed alongside preceding items without boundary or volume overlap."
                ),
                execution_time_ms=elapsed_ms,
            )

        # Successful packing! Calculate utilization metrics
        total_item_vol = sum(it.volume for it in items)
        total_item_wt = sum(it.weight for it in items)

        vol_util = Decimal("0.00")
        if box.volume > Decimal("0.00"):
            vol_util = Decimal(f"{(total_item_vol / box.volume * Decimal('100.00')):.2f}")

        wt_util = Decimal("0.00")
        if box.max_weight > Decimal("0.00"):
            wt_util = Decimal(f"{(total_item_wt / box.max_weight * Decimal('100.00')):.2f}")

        return PackingResultDTO(
            is_feasible=True,
            box=box,
            placed_items=placements,
            unplaced_items=[],
            volume_utilization_pct=vol_util,
            weight_utilization_pct=wt_util,
            execution_time_ms=elapsed_ms,
        )

