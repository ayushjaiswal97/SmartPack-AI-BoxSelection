from decimal import Decimal
from typing import List, Optional, Tuple
from .dataclasses import BoxDTO, ItemDTO, PackingResultDTO
from .algorithms.extreme_points import ExtremePointsPacker


class BoxSelectorService:
    """
    Orchestrates the selection of the lowest-cost feasible box for an order.
    
    Adheres strictly to the business rules:
    1. Filter out physically or volumetrically impossible boxes early.
    2. Sort remaining candidate boxes by packaging cost ascending.
    3. Apply tie-breaking rules (lower internal volume, then lower max weight).
    4. Run 3D rotational packing to guarantee physical fit without collision.
    5. Terminate and return the first feasible box (guaranteed lowest cost).
    """

    def __init__(self, allow_upright_only: bool = False):
        self.packer = ExtremePointsPacker(allow_upright_only=allow_upright_only)

    def select_best_box(
        self,
        items: List[ItemDTO],
        candidate_boxes: List[BoxDTO],
    ) -> Tuple[Optional[PackingResultDTO], List[str]]:
        """
        Evaluates candidate boxes and returns (best_result, audit_log).
        If no box fits, best_result.is_feasible will be False.
        """
        audit_log: List[str] = []

        if not candidate_boxes:
            audit_log.append("No active shipping boxes available in catalog.")
            return PackingResultDTO(
                is_feasible=False,
                failure_reason="No active shipping boxes are configured in the system.",
            ), audit_log

        if not items:
            audit_log.append("Order contains no items.")
            return PackingResultDTO(
                is_feasible=False,
                failure_reason="The order does not contain any items to pack.",
            ), audit_log

        # Calculate order aggregates for logging
        total_weight = sum(item.weight for item in items)
        total_volume = sum(item.volume for item in items)
        audit_log.append(
            f"Evaluating order with {len(items)} discrete items. "
            f"Total Weight: {total_weight:.3f} kg, Total Volume: {total_volume:,.1f} cm³."
        )

        # Sort candidate boxes by cost (primary), then volume (secondary tie-break),
        # then max_weight (tertiary tie-break)
        sorted_boxes = sorted(
            candidate_boxes,
            key=lambda b: (b.packaging_cost, b.volume, b.max_weight, b.name),
        )

        evaluation_failures: List[str] = []

        for box in sorted_boxes:
            result = self.packer.pack(items, box)

            if result.is_feasible:
                audit_log.append(
                    f"Box selected: '{box.name}' at cost ${box.packaging_cost:.2f} "
                    f"(Volume Utilization: {result.volume_utilization_pct}%, "
                    f"Weight Utilization: {result.weight_utilization_pct}%)."
                )
                return result, audit_log
            else:
                evaluation_failures.append(f"{box.name}: {result.failure_reason}")
                audit_log.append(f"Box '{box.name}' disqualified: {result.failure_reason}")

        # If we reached here, no candidate box could fit the complete order
        reasons_summary = " | ".join(evaluation_failures[:3])
        if len(evaluation_failures) > 3:
            reasons_summary += f" (...and {len(evaluation_failures) - 3} more boxes evaluated)"

        failure_msg = (
            f"Order cannot fit in any available single shipping box. "
            f"Evaluated {len(sorted_boxes)} candidate boxes. Constraints encountered: {reasons_summary}"
        )

        return PackingResultDTO(
            is_feasible=False,
            unplaced_items=list(items),
            failure_reason=failure_msg,
        ), audit_log

