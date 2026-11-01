from decimal import Decimal
from typing import List, Optional, Tuple
from .dataclasses import BoxDTO, BoxEvaluationSummary, ItemDTO, PackingResultDTO
from .core import (
    calculate_total_order_weight,
    evaluate_box_candidates,
    select_optimal_box,
)


class BoxSelectorService:
    """
    Service interface wrapper for evaluating candidate boxes and
    selecting the optimal box for an order.
    """

    def __init__(self, allow_upright_only: bool = False):
        self.allow_upright_only = allow_upright_only

    def select_best_box(
        self,
        items: List[ItemDTO],
        candidate_boxes: List[BoxDTO],
    ) -> Tuple[Optional[PackingResultDTO], List[str]]:
        """
        Evaluates candidate boxes and returns (winning_result, audit_log).
        """
        audit_log: List[str] = []

        total_weight = calculate_total_order_weight(items)
        total_volume = sum((item.volume for item in items), Decimal("0.00"))

        audit_log.append(
            f"Evaluating order with {len(items)} discrete items. "
            f"Total Weight: {total_weight:.3f} kg, Total Volume: {total_volume:,.1f} cm³."
        )

        winning_result, summaries = select_optimal_box(items, candidate_boxes)

        for summary in summaries:
            if summary.is_feasible:
                audit_log.append(
                    f"Box '{summary.box_name}' feasible: Cost ₹{summary.packaging_cost} "
                    f"(Vol: {summary.volume_utilization_pct}%, Wt: {summary.weight_utilization_pct}%)."
                )
            else:
                audit_log.append(f"Box '{summary.box_name}' rejected: {summary.rejection_reason}")

        if winning_result and winning_result.is_feasible and winning_result.box:
            audit_log.append(f"Selected lowest-cost feasible box: '{winning_result.box.name}'.")
        else:
            audit_log.append("No feasible box could accommodate the order.")

        return winning_result, audit_log
