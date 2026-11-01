from decimal import Decimal
from typing import List, Tuple
from django.db import transaction
from apps.catalog.models import ShippingBox
from apps.orders.models import Order, OrderItem, PackingResult
from apps.packing_engine.dataclasses import BoxDTO, ItemDTO
from apps.packing_engine.selector import BoxSelectorService


def build_item_dtos_from_order(order: Order) -> List[ItemDTO]:
    """
    Expands an order's items into discrete ItemDTO instances
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
    qs = ShippingBox.objects.all()
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
        )
        for box in qs
    ]


@transaction.atomic
def evaluate_and_pack_order(
    order: Order,
    allow_upright_only: bool = False,
) -> Tuple[Order, PackingResult, List[str]]:
    """
    Evaluates an order against candidate shipping boxes, selecting the
    lowest-cost feasible box using 3D rotational bin packing.
    Persists results to Order and PackingResult models.
    """
    items = build_item_dtos_from_order(order)
    boxes = build_box_dtos(active_only=True)

    # Compute order aggregates
    total_weight = sum((item.weight for item in items), Decimal("0.000"))
    total_volume = sum((item.volume for item in items), Decimal("0.00"))

    order.total_weight = total_weight
    order.total_volume = total_volume

    selector = BoxSelectorService(allow_upright_only=allow_upright_only)
    packing_result_dto, audit_log = selector.select_best_box(items, boxes)

    if packing_result_dto.is_feasible and packing_result_dto.box:
        box_model = ShippingBox.objects.get(id=packing_result_dto.box.box_id)
        order.selected_box = box_model
        order.packaging_cost = box_model.packaging_cost
        order.status = Order.STATUS_EVALUATED
    else:
        order.selected_box = None
        order.packaging_cost = None
        order.status = Order.STATUS_FAILED

    order.save()

    # Persist or update PackingResult
    packing_result, _ = PackingResult.objects.update_or_create(
        order=order,
        defaults={
            'is_feasible': packing_result_dto.is_feasible,
            'failure_reason': packing_result_dto.failure_reason,
            'volume_utilization_pct': packing_result_dto.volume_utilization_pct,
            'weight_utilization_pct': packing_result_dto.weight_utilization_pct,
            'placed_items_manifest': [p.to_dict() for p in packing_result_dto.placed_items],
            'execution_time_ms': packing_result_dto.execution_time_ms,
        },
    )

    return order, packing_result, audit_log

