import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple, Union
from django.db import DatabaseError, transaction
from apps.catalog.models import Box
from apps.orders.exceptions import EmptyOrderError, OrderNotFoundError, PackagingServiceError
from apps.orders.models import Order, OrderItem, PackingResult
from apps.packing_engine.core import (
    calculate_total_order_weight,
    evaluate_box_candidates,
    select_optimal_box,
)
from apps.packing_engine.dataclasses import BoxDTO, ItemDTO, PackingResultDTO

logger = logging.getLogger(__name__)


def build_item_dtos_from_order(order: Order) -> List[ItemDTO]:
    """
    Expands an order's line items into discrete ItemDTO instances
    taking product physical attributes and quantities into account.
    """
    items: List[ItemDTO] = []
    for order_item in order.items.select_related('product').all():
        prod = order_item.product
        l = order_item.unit_length_snapshot or prod.length
        w = order_item.unit_width_snapshot or prod.width
        h = order_item.unit_height_snapshot or prod.height
        wt = order_item.unit_weight_snapshot or prod.weight

        for unit_idx in range(1, order_item.quantity + 1):
            items.append(
                ItemDTO(
                    item_id=f"{prod.sku}#{unit_idx}",
                    sku=prod.sku,
                    name=prod.name,
                    length=l,
                    width=w,
                    height=h,
                    weight=wt,
                )
            )
    return items


def build_box_dtos(active_only: bool = True) -> List[BoxDTO]:
    """Fetches candidate shipping boxes from the database and converts to BoxDTOs."""
    qs = Box.objects.all()
    if active_only:
        qs = qs.filter(is_active=True)

    return [
        BoxDTO(
            box_id=box.id,
            name=box.name,
            length=box.internal_length,
            width=box.internal_width,
            height=box.internal_height,
            max_weight=box.max_weight_capacity,
            packaging_cost=box.packaging_cost,
            is_active=box.is_active,
        )
        for box in qs
    ]


class PackagingService:
    """
    Dedicated enterprise service orchestrating box recommendations,
    candidate evaluations, and state persistence for customer orders.
    """

    @classmethod
    def get_order_by_identifier(cls, order_identifier: Union[int, str]) -> Order:
        """
        Retrieves an order by primary key ID or unique order_number reference.
        Optimized with prefetching to eliminate N+1 queries.
        """
        qs = Order.objects.prefetch_related('items__product').select_related('selected_box', 'packing_result')
        
        order = None
        # Try integer ID match
        if isinstance(order_identifier, int) or (isinstance(order_identifier, str) and order_identifier.isdigit()):
            order = qs.filter(id=int(order_identifier)).first()

        # If not found or string reference, try order_number match
        if not order and isinstance(order_identifier, str):
            order = qs.filter(order_number=order_identifier).first()

        if not order:
            raise OrderNotFoundError(f"Order '{order_identifier}' does not exist.")

        return order

    @classmethod
    def recommend_box_for_order(
        cls,
        order_identifier: Union[int, str],
        allow_upright_only: bool = False,
    ) -> Dict[str, Any]:
        """
        Core service pipeline:
          1. Retrieve Order & OrderItems via ORM.
          2. Validate item presence.
          3. Fetch active shipping box candidates.
          4. Execute 3D packing engine & candidate evaluations.
          5. Atomically update Order and PackingResult persistence models.
          6. Return comprehensive structured result.
        """
        order = cls.get_order_by_identifier(order_identifier)

        # Validate order has items using prefetched cache
        if not order.items.all():
            raise EmptyOrderError(f"Order '{order.order_number}' contains no items to pack.")

        items = build_item_dtos_from_order(order)
        active_boxes = build_box_dtos(active_only=True)

        total_weight = calculate_total_order_weight(items)
        total_volume = sum((item.volume for item in items), Decimal("0.00"))

        # Evaluate candidate boxes to produce detailed audit logs
        candidate_summaries = evaluate_box_candidates(items, active_boxes)

        # Select optimal box
        winning_result, _ = select_optimal_box(items, active_boxes)

        # Persist results in atomic transaction
        try:
            with transaction.atomic():
                order.total_weight = total_weight
                order.total_volume = total_volume

                if winning_result and winning_result.is_feasible and winning_result.box:
                    order.selected_box_id = winning_result.box.box_id
                    order.packaging_cost = winning_result.box.packaging_cost
                    order.status = Order.Status.EVALUATED
                else:
                    order.selected_box = None
                    order.packaging_cost = None
                    order.status = Order.Status.FAILED

                order.save()

                if winning_result:
                    PackingResult.objects.update_or_create(
                        order=order,
                        defaults={
                            'is_feasible': winning_result.is_feasible,
                            'failure_reason': winning_result.failure_reason,
                            'volume_utilization_pct': winning_result.volume_utilization_pct,
                            'weight_utilization_pct': winning_result.weight_utilization_pct,
                            'placed_items_manifest': [p.to_dict() for p in winning_result.placed_items],
                            'execution_time_ms': winning_result.execution_time_ms,
                        },
                    )
        except DatabaseError as db_err:
            logger.error("Database error while persisting packing result for order %s: %s", order.order_number, db_err)
            raise

        # Build structured response payload
        is_feasible = bool(winning_result and winning_result.is_feasible and winning_result.box)

        selected_box_data = None
        if is_feasible and winning_result.box:
            b = winning_result.box
            selected_box_data = {
                "id": b.box_id,
                "name": b.name,
                "dimensions": {
                    "length": float(b.length),
                    "width": float(b.width),
                    "height": float(b.height),
                    "unit": "cm",
                },
                "max_weight_capacity": float(b.max_weight),
                "packaging_cost": float(b.packaging_cost),
            }

        # Build list of rejected / non-selected boxes with reasons
        rejected_boxes_data = []
        for s in candidate_summaries:
            if is_feasible and winning_result.box and s.box_id == winning_result.box.box_id:
                continue  # This was the winning box

            box_obj = next((b for b in active_boxes if b.box_id == s.box_id), None)
            reason = s.rejection_reason
            if s.is_feasible and is_feasible:
                reason = "Feasible, but higher packaging cost than selected box."

            rejected_boxes_data.append({
                "id": s.box_id,
                "name": s.box_name,
                "dimensions": {
                    "length": float(box_obj.length) if box_obj else 0.0,
                    "width": float(box_obj.width) if box_obj else 0.0,
                    "height": float(box_obj.height) if box_obj else 0.0,
                    "unit": "cm",
                },
                "max_weight_capacity": float(box_obj.max_weight) if box_obj else 0.0,
                "packaging_cost": float(s.packaging_cost),
                "rejection_reason": reason,
            })

        explanation = (
            f"Box '{winning_result.box.name}' selected as the lowest-cost feasible box (${winning_result.box.packaging_cost})."
            if is_feasible and winning_result.box
            else (winning_result.failure_reason if winning_result else "No suitable box could be found.")
        )

        return {
            "order_number": order.order_number,
            "customer_reference": order.customer_reference,
            "selection_status": "FEASIBLE" if is_feasible else "INFEASIBLE",
            "total_order_weight": float(total_weight),
            "total_order_volume": float(total_volume),
            "selected_box": selected_box_data,
            "packaging_cost": float(winning_result.box.packaging_cost) if (is_feasible and winning_result.box) else None,
            "volume_utilization_pct": float(winning_result.volume_utilization_pct) if winning_result else 0.0,
            "weight_utilization_pct": float(winning_result.weight_utilization_pct) if winning_result else 0.0,
            "explanation": explanation,
            "rejected_boxes": rejected_boxes_data,
            "placed_items": [p.to_dict() for p in winning_result.placed_items] if winning_result else [],
            "execution_time_ms": winning_result.execution_time_ms if winning_result else 0,
        }


# Legacy helper alias for existing views
def evaluate_and_pack_order(
    order: Order,
    allow_upright_only: bool = False,
) -> Tuple[Order, PackingResult, List[str]]:
    """Backward-compatible helper wrapping PackagingService."""
    res = PackagingService.recommend_box_for_order(order.id, allow_upright_only=allow_upright_only)
    order.refresh_from_db()
    packing_result = getattr(order, 'packing_result', None)
    audit_log = [res.get('explanation', '')]
    return order, packing_result, audit_log
