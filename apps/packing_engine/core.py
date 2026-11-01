import time
from decimal import Decimal
from typing import List, Optional, Tuple
from .dataclasses import BoxDTO, BoxEvaluationSummary, ItemDTO, PlacementDTO, PackingResultDTO


# ============================================================================
# 1. Total Weight Calculation
# ============================================================================

def calculate_total_order_weight(items: List[ItemDTO]) -> Decimal:
    """
    Calculates the exact total gross weight of all items in an order.
    
    Uses Decimal arithmetic to prevent floating-point drift.
    Returns Decimal('0.000') for empty item lists.
    """
    if not items:
        return Decimal("0.000")
    return sum((item.weight for item in items), Decimal("0.000"))


# ============================================================================
# 2. Orthogonal 3D Orientations Generator
# ============================================================================

def generate_valid_orientations(
    length: Decimal,
    width: Decimal,
    height: Decimal,
) -> List[Tuple[Decimal, Decimal, Decimal]]:
    """
    Generates all six axis-aligned orthogonal 3D orientations (dx, dy, dz)
    for a rectangular cuboid.
    
    Eliminates duplicate orientations for symmetric cuboids (cubes have 1,
    square prisms have 3) while preserving deterministic order.
    """
    candidate_rotations = [
        (length, width, height),
        (length, height, width),
        (width, length, height),
        (width, height, length),
        (height, length, width),
        (height, width, length),
    ]

    unique_rotations: List[Tuple[Decimal, Decimal, Decimal]] = []
    seen = set()
    for rot in candidate_rotations:
        if rot not in seen:
            seen.add(rot)
            unique_rotations.append(rot)

    return unique_rotations


# ============================================================================
# 3. Single-Product Dimensional & Weight Fit Check
# ============================================================================

def check_single_product_fit(item: ItemDTO, box: BoxDTO) -> Tuple[bool, Optional[str]]:
    """
    Evaluates whether a single product can independently fit inside a box
    under at least one of its six orthogonal rotations, without exceeding
    the box's maximum weight capacity.
    
    Returns (True, None) if compatible, or (False, rejection_reason).
    """
    if item.weight > box.max_weight:
        deficit = item.weight - box.max_weight
        return False, (
            f"Item '{item.sku}' weight ({item.weight} kg) exceeds box maximum weight capacity "
            f"({box.max_weight} kg) by {deficit} kg."
        )

    item_sorted = item.sorted_dimensions
    box_sorted = box.sorted_dimensions

    # If sorted dimensions fail, no rotation in 3D can fit inside the box
    if not (
        item_sorted[0] <= box_sorted[0]
        and item_sorted[1] <= box_sorted[1]
        and item_sorted[2] <= box_sorted[2]
    ):
        return False, (
            f"Item '{item.sku}' dimensions ({item.length}x{item.width}x{item.height} cm) "
            f"exceed box '{box.name}' internal clearance ({box.length}x{box.width}x{box.height} cm) "
            f"under all six 3D orthogonal orientations."
        )

    return True, None


# ============================================================================
# 4. Multi-Product 3D Spatial Feasibility (Extreme Points Heuristic)
# ============================================================================

def _check_boxes_overlap(
    p1_x: Decimal, p1_y: Decimal, p1_z: Decimal,
    d1_x: Decimal, d1_y: Decimal, d1_z: Decimal,
    p2_x: Decimal, p2_y: Decimal, p2_z: Decimal,
    d2_x: Decimal, d2_y: Decimal, d2_z: Decimal,
) -> bool:
    """Returns True if two 3D cuboids overlap in open spatial volume."""
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
    """Returns True if point (px, py, pz) is strictly enclosed within a placed box."""
    return (
        bx <= px < bx + bdx
        and by <= py < by + bdy
        and bz <= pz < bz + bdz
    )


def check_multi_product_spatial_feasibility(
    items: List[ItemDTO],
    box: BoxDTO,
) -> PackingResultDTO:
    """
    Evaluates whether all products can physically pack together inside the box
    without overlapping, under 6-axis orthogonal rotations.
    
    Strategy: 3D Extreme Points (EP) Heuristic with Best-Fit Decreasing (BFD) sorting.
    """
    start_time = time.perf_counter()

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

    # Pre-condition 1: Weight capacity
    total_weight = calculate_total_order_weight(items)
    if total_weight > box.max_weight:
        deficit = total_weight - box.max_weight
        return PackingResultDTO(
            is_feasible=False,
            box=box,
            unplaced_items=list(items),
            failure_reason=(
                f"Total order weight ({total_weight:.3f} kg) exceeds box maximum capacity "
                f"({box.max_weight:.3f} kg) by {deficit:.3f} kg."
            ),
            execution_time_ms=int((time.perf_counter() - start_time) * 1000),
        )

    # Pre-condition 2: Volumetric necessary condition
    total_item_volume = sum((item.volume for item in items), Decimal("0.00"))
    if total_item_volume > box.volume:
        vol_deficit = total_item_volume - box.volume
        return PackingResultDTO(
            is_feasible=False,
            box=box,
            unplaced_items=list(items),
            failure_reason=(
                f"Total items volume ({total_item_volume:,.1f} cm³) exceeds box internal volume "
                f"({box.volume:,.1f} cm³) by {vol_deficit:,.1f} cm³."
            ),
            execution_time_ms=int((time.perf_counter() - start_time) * 1000),
        )

    # Pre-condition 3: Single-item dimensional viability
    for item in items:
        single_fit, reason = check_single_product_fit(item, box)
        if not single_fit:
            return PackingResultDTO(
                is_feasible=False,
                box=box,
                unplaced_items=list(items),
                failure_reason=reason or "Single-item dimensional bounds exceeded.",
                execution_time_ms=int((time.perf_counter() - start_time) * 1000),
            )

    # Best-Fit Decreasing (BFD) item sorting:
    # Anchor large items first to minimize fragmented dead space.
    sorted_items = sorted(
        items,
        key=lambda it: (it.volume, max(it.length, it.width, it.height)),
        reverse=True,
    )

    box_l = box.length
    box_w = box.width
    box_h = box.height

    # Candidate placement coordinates (x, y, z)
    extreme_points: List[Tuple[Decimal, Decimal, Decimal]] = [
        (Decimal("0.00"), Decimal("0.00"), Decimal("0.00"))
    ]
    placements: List[PlacementDTO] = []
    unplaced_items: List[ItemDTO] = []

    for item in sorted_items:
        rotations = generate_valid_orientations(item.length, item.width, item.height)
        placed = False

        # Evaluate candidate points sorted by lowest Z (gravity/bottom first), then Y, then X
        for pt in list(extreme_points):
            px, py, pz = pt

            for dx, dy, dz in rotations:
                # Boundary check against box internal walls
                if px + dx > box_l or py + dy > box_w or pz + dz > box_h:
                    continue

                # Collision check with all already placed items
                collision = False
                for p in placements:
                    if _check_boxes_overlap(
                        px, py, pz, dx, dy, dz,
                        p.x, p.y, p.z, p.dx, p.dy, p.dz,
                    ):
                        collision = True
                        break

                if not collision:
                    # Valid physical placement found!
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

                    # Generate new candidate extreme points
                    new_points = [
                        (px + dx, py, pz),
                        (px, py + dy, pz),
                        (px, py, pz + dz),
                    ]

                    # Edge projection onto existing items
                    for ex in placements:
                        if ex.x + ex.dx > px and ex.x + ex.dx <= box_l:
                            new_points.append((ex.x + ex.dx, py, pz))
                        if ex.y + ex.dy > py and ex.y + ex.dy <= box_w:
                            new_points.append((px, ex.y + ex.dy, pz))
                        if ex.z + ex.dz > pz and ex.z + ex.dz <= box_h:
                            new_points.append((px, py, ex.z + ex.dz))

                    # Filter points: must stay inside box and not lie inside placed items
                    all_candidates = set(extreme_points + new_points)
                    valid_points = []

                    for cand_x, cand_y, cand_z in all_candidates:
                        if cand_x >= box_l or cand_y >= box_w or cand_z >= box_h:
                            continue

                        inside_any = False
                        for pl in placements:
                            if _point_is_inside_box(
                                cand_x, cand_y, cand_z,
                                pl.x, pl.y, pl.z, pl.dx, pl.dy, pl.dz,
                            ):
                                inside_any = True
                                break

                        if not inside_any:
                            valid_points.append((cand_x, cand_y, cand_z))

                    # Re-sort points: lowest Z, then lowest Y, then lowest X
                    valid_points.sort(key=lambda p: (p[2], p[1], p[0]))
                    extreme_points = valid_points
                    break  # Break rotations loop

            if placed:
                break  # Break points loop

        if not placed:
            unplaced_items.append(item)
            break  # Early termination: if an item cannot be packed, box fails

    elapsed_ms = max(1, int((time.perf_counter() - start_time) * 1000))

    if unplaced_items:
        failed = unplaced_items[0]
        return PackingResultDTO(
            is_feasible=False,
            box=box,
            placed_items=placements,
            unplaced_items=unplaced_items,
            failure_reason=(
                f"3D Spatial packing infeasible: Item '{failed.sku}' "
                f"({failed.length}x{failed.width}x{failed.height} cm) cannot be placed inside box '{box.name}' "
                f"without colliding with other packed items or exceeding box clearance."
            ),
            execution_time_ms=elapsed_ms,
        )

    # Success: calculate exact utilization percentages
    vol_util = Decimal("0.00")
    if box.volume > Decimal("0.00"):
        vol_util = Decimal(f"{(total_item_volume / box.volume * Decimal('100.00')):.2f}")

    wt_util = Decimal("0.00")
    if box.max_weight > Decimal("0.00"):
        wt_util = Decimal(f"{(total_weight / box.max_weight * Decimal('100.00')):.2f}")

    return PackingResultDTO(
        is_feasible=True,
        box=box,
        placed_items=placements,
        unplaced_items=[],
        volume_utilization_pct=vol_util,
        weight_utilization_pct=wt_util,
        execution_time_ms=elapsed_ms,
    )


# ============================================================================
# 5. Candidate Boxes Evaluation
# ============================================================================

def evaluate_box_candidates(
    items: List[ItemDTO],
    boxes: List[BoxDTO],
) -> List[BoxEvaluationSummary]:
    """
    Evaluates an order against all candidate boxes, producing a comprehensive
    audit summary explaining why each box was selected or rejected.
    """
    summaries: List[BoxEvaluationSummary] = []
    total_order_weight = calculate_total_order_weight(items)
    total_order_volume = sum((item.volume for item in items), Decimal("0.00"))

    for box in boxes:
        if not box.is_active:
            summaries.append(
                BoxEvaluationSummary(
                    box_id=box.box_id,
                    box_name=box.name,
                    packaging_cost=box.packaging_cost,
                    is_active=False,
                    is_feasible=False,
                    rejection_reason="Box is marked as inactive in warehouse catalog.",
                    weight_feasible=False,
                    volume_feasible=False,
                    dimensional_feasible=False,
                    spatial_feasible=False,
                )
            )
            continue

        wt_ok = total_order_weight <= box.max_weight
        vol_ok = total_order_volume <= box.volume

        # Individual dimensions check
        dim_ok = True
        dim_reason = ""
        for it in items:
            single_fit, reason = check_single_product_fit(it, box)
            if not single_fit:
                dim_ok = False
                dim_reason = reason or "Single product exceeds clearance."
                break

        if not wt_ok:
            summaries.append(
                BoxEvaluationSummary(
                    box_id=box.box_id,
                    box_name=box.name,
                    packaging_cost=box.packaging_cost,
                    is_active=True,
                    is_feasible=False,
                    rejection_reason=f"Exceeds max weight capacity ({total_order_weight:.3f} kg > {box.max_weight:.3f} kg).",
                    weight_feasible=False,
                    volume_feasible=vol_ok,
                    dimensional_feasible=dim_ok,
                    spatial_feasible=False,
                )
            )
            continue

        if not vol_ok:
            summaries.append(
                BoxEvaluationSummary(
                    box_id=box.box_id,
                    box_name=box.name,
                    packaging_cost=box.packaging_cost,
                    is_active=True,
                    is_feasible=False,
                    rejection_reason=f"Exceeds internal volume ({total_order_volume:,.1f} cm³ > {box.volume:,.1f} cm³).",
                    weight_feasible=True,
                    volume_feasible=False,
                    dimensional_feasible=dim_ok,
                    spatial_feasible=False,
                )
            )
            continue

        if not dim_ok:
            summaries.append(
                BoxEvaluationSummary(
                    box_id=box.box_id,
                    box_name=box.name,
                    packaging_cost=box.packaging_cost,
                    is_active=True,
                    is_feasible=False,
                    rejection_reason=dim_reason,
                    weight_feasible=True,
                    volume_feasible=True,
                    dimensional_feasible=False,
                    spatial_feasible=False,
                )
            )
            continue

        # Run 3D spatial packing test
        packing_res = check_multi_product_spatial_feasibility(items, box)
        summaries.append(
            BoxEvaluationSummary(
                box_id=box.box_id,
                box_name=box.name,
                packaging_cost=box.packaging_cost,
                is_active=True,
                is_feasible=packing_res.is_feasible,
                rejection_reason="" if packing_res.is_feasible else packing_res.failure_reason,
                weight_feasible=True,
                volume_feasible=True,
                dimensional_feasible=True,
                spatial_feasible=packing_res.is_feasible,
                volume_utilization_pct=packing_res.volume_utilization_pct,
                weight_utilization_pct=packing_res.weight_utilization_pct,
                packing_result=packing_res,
            )
        )

    return summaries


# ============================================================================
# 6. Optimal Box Selection
# ============================================================================

def select_optimal_box(
    items: List[ItemDTO],
    boxes: List[BoxDTO],
) -> Tuple[Optional[PackingResultDTO], List[BoxEvaluationSummary]]:
    """
    Selects the lowest-cost available shipping box capable of safely accommodating
    all items in an order.
    
    Tie-breaking hierarchy when costs are equal:
      1. Lowest packaging cost ($) (Primary objective)
      2. Smallest internal volume (cm³) (Minimizes void fill and carrier dimensional freight)
      3. Smallest maximum weight capacity (kg) (Preserves heavy-duty boxes for heavier orders)
      4. Alphabetical box name (Guarantees 100% deterministic reproducibility)
    
    Returns (winning_packing_result, full_box_audit_summaries).
    If no box is feasible, winning_packing_result is None or has is_feasible=False.
    """
    if not items:
        return (
            PackingResultDTO(
                is_feasible=False,
                failure_reason="The order contains no items to pack.",
            ),
            [],
        )

    active_boxes = [b for b in boxes if b.is_active]
    if not active_boxes:
        return (
            PackingResultDTO(
                is_feasible=False,
                failure_reason="No active shipping boxes are configured in the system.",
            ),
            [],
        )

    # Sort candidates deterministically according to our cost & tie-breaking rules
    sorted_candidates = sorted(
        active_boxes,
        key=lambda b: (b.packaging_cost, b.volume, b.max_weight, b.name),
    )

    evaluation_summaries: List[BoxEvaluationSummary] = []
    winning_result: Optional[PackingResultDTO] = None

    for candidate in sorted_candidates:
        result = check_multi_product_spatial_feasibility(items, candidate)
        summary = BoxEvaluationSummary(
            box_id=candidate.box_id,
            box_name=candidate.name,
            packaging_cost=candidate.packaging_cost,
            is_active=True,
            is_feasible=result.is_feasible,
            rejection_reason="" if result.is_feasible else result.failure_reason,
            weight_feasible=calculate_total_order_weight(items) <= candidate.max_weight,
            volume_feasible=sum((it.volume for it in items), Decimal("0.00")) <= candidate.volume,
            dimensional_feasible=result.is_feasible,
            spatial_feasible=result.is_feasible,
            volume_utilization_pct=result.volume_utilization_pct,
            weight_utilization_pct=result.weight_utilization_pct,
            packing_result=result,
        )
        evaluation_summaries.append(summary)

        if result.is_feasible and winning_result is None:
            # Because boxes were pre-sorted by cost ASC, the first feasible box
            # is mathematically guaranteed to be the lowest-cost option!
            winning_result = result
            # We can break early, but to provide full audit summaries for reporting,
            # we can evaluate remaining boxes or return the winner immediately.
            break

    # If all sorted candidates failed
    if winning_result is None:
        reasons = [s.rejection_reason for s in evaluation_summaries if s.rejection_reason]
        reasons_summary = " | ".join(reasons[:3])
        winning_result = PackingResultDTO(
            is_feasible=False,
            unplaced_items=list(items),
            failure_reason=(
                f"Order cannot fit in any available active shipping box. "
                f"Evaluated {len(sorted_candidates)} candidate boxes. Constraints encountered: {reasons_summary}"
            ),
        )

    return winning_result, evaluation_summaries

