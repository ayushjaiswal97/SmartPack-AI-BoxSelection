import json
import logging
from decimal import Decimal
from django.db import DatabaseError, transaction
from django.http import JsonResponse
from django.views import View
from apps.catalog.models import Product
from apps.orders.exceptions import EmptyOrderError, OrderNotFoundError
from apps.orders.models import Order, OrderItem
from apps.orders.services import PackagingService, evaluate_and_pack_order

logger = logging.getLogger(__name__)


def serialize_order_summary(order: Order) -> dict:
    # Use prefetched objects cache if available to prevent N+1 query per order
    if hasattr(order, '_prefetched_objects_cache') and 'items' in order._prefetched_objects_cache:
        items_count = len(order.items.all())
    else:
        items_count = order.items.count()

    return {
        "id": order.id,
        "order_number": order.order_number,
        "customer_reference": order.customer_reference,
        "status": order.status,
        "status_display": order.get_status_display(),
        "total_order_weight": float(order.total_weight),
        "total_volume": float(order.total_volume),
        "packaging_cost": float(order.packaging_cost) if order.packaging_cost else None,
        "selected_box": order.selected_box.name if order.selected_box else None,
        "items_count": items_count,
        "created_at": order.created_at.isoformat(),
        "updated_at": order.updated_at.isoformat(),
    }


def serialize_order_detail(order: Order) -> dict:
    items = []
    # Avoid duplicate query if items__product is already in prefetch cache
    item_qs = (
        order.items.all()
        if hasattr(order, '_prefetched_objects_cache') and 'items' in order._prefetched_objects_cache
        else order.items.select_related('product').all()
    )
    for item in item_qs:
        items.append({
            "id": item.id,
            "product_id": item.product_id,
            "sku": item.product.sku,
            "name": item.product.name,
            "quantity": item.quantity,
            "unit_length": float(item.unit_length_snapshot or item.product.length),
            "unit_width": float(item.unit_width_snapshot or item.product.width),
            "unit_height": float(item.unit_height_snapshot or item.product.height),
            "unit_weight": float(item.unit_weight_snapshot or item.product.weight),
            "total_weight": float(item.total_weight),
            "total_volume": float(item.total_volume),
        })

    packing_result_data = None
    if hasattr(order, 'packing_result') and order.packing_result:
        res = order.packing_result
        packing_result_data = {
            "is_feasible": res.is_feasible,
            "failure_reason": res.failure_reason,
            "volume_utilization_pct": float(res.volume_utilization_pct),
            "weight_utilization_pct": float(res.weight_utilization_pct),
            "placed_items_manifest": res.placed_items_manifest,
            "execution_time_ms": float(res.execution_time_ms),
        }

    summary = serialize_order_summary(order)
    summary["notes"] = order.notes
    summary["items"] = items
    summary["packing_result"] = packing_result_data
    return summary


class RecommendBoxAPIView(View):
    """
    REST API Endpoint: POST /api/orders/<order_id>/recommend-box/
    
    Evaluates an order against all active warehouse shipping boxes using
    the 3D Extreme Points bin packing engine and returns the lowest-cost
    feasible box recommendation along with audit reasons.
    """

    def post(self, request, order_id: str, *args, **kwargs):
        try:
            result = PackagingService.recommend_box_for_order(order_id)
            return JsonResponse(result, status=200)

        except OrderNotFoundError as exc:
            return JsonResponse(
                {
                    "error": "Not Found",
                    "detail": str(exc),
                },
                status=404,
            )

        except EmptyOrderError as exc:
            return JsonResponse(
                {
                    "error": "Bad Request",
                    "detail": str(exc),
                },
                status=400,
            )

        except DatabaseError as exc:
            logger.exception("Database error during packaging recommendation for order '%s': %s", order_id, exc)
            return JsonResponse(
                {
                    "error": "Internal Server Error",
                    "detail": "A database error occurred while processing the order.",
                },
                status=500,
            )

        except Exception as exc:
            logger.exception("Unexpected error during packaging recommendation for order '%s': %s", order_id, exc)
            return JsonResponse(
                {
                    "error": "Internal Server Error",
                    "detail": "An unexpected server error occurred.",
                },
                status=500,
            )


class OrderListCreateAPIView(View):
    """
    GET  /api/orders/  - List recent customer orders
    POST /api/orders/  - Create an order with line items and optionally run packaging recommendation
    """

    def get(self, request, *args, **kwargs):
        try:
            from django.db.models import Q
            qs = (
                Order.objects.select_related('selected_box', 'packing_result')
                .prefetch_related('items__product')
                .order_by('-created_at')
            )
            q = request.GET.get('q', '').strip()
            status_param = request.GET.get('status')
            if q:
                qs = qs.filter(Q(order_number__icontains=q) | Q(customer_reference__icontains=q))
            if status_param and status_param in [s.value for s in Order.Status]:
                qs = qs.filter(status=status_param)

            limit = min(int(request.GET.get('limit', 50)), 100)
            orders = [serialize_order_summary(o) for o in qs[:limit]]
            return JsonResponse({"orders": orders, "count": len(orders)}, status=200)
        except Exception as exc:
            logger.exception("Error listing orders: %s", exc)
            return JsonResponse({"error": "Internal Server Error", "detail": "Failed to fetch orders."}, status=500)

    def post(self, request, *args, **kwargs):
        try:
            if request.content_type == 'application/json':
                data = json.loads(request.body.decode('utf-8'))
            else:
                data = request.POST.dict()
        except json.JSONDecodeError:
            return JsonResponse({"error": "Bad Request", "detail": "Malformed JSON payload."}, status=400)

        # Validate order line items
        raw_items = data.get('items', [])
        if not raw_items or not isinstance(raw_items, list):
            return JsonResponse(
                {
                    "error": "Validation Error",
                    "detail": "An order must contain at least one line item in 'items'.",
                    "errors": {"items": ["Please add at least one product with a quantity of 1 or more."]},
                },
                status=400,
            )

        errors = {}
        validated_items = []
        for idx, item in enumerate(raw_items):
            prod_id = item.get('product_id') or item.get('product')
            qty = item.get('quantity')
            if not prod_id:
                errors[f"items[{idx}].product"] = ["Product ID is required."]
                continue
            try:
                prod = Product.objects.get(pk=prod_id)
            except (Product.DoesNotExist, ValueError):
                errors[f"items[{idx}].product"] = [f"Product with ID '{prod_id}' does not exist."]
                continue

            try:
                qty_int = int(qty)
                if qty_int < 1:
                    errors[f"items[{idx}].quantity"] = ["Quantity must be at least 1."]
                    continue
            except (TypeError, ValueError):
                errors[f"items[{idx}].quantity"] = ["Quantity must be a positive integer."]
                continue

            validated_items.append((prod, qty_int))

        if errors:
            return JsonResponse(
                {
                    "error": "Validation Error",
                    "detail": "Line item validation failed.",
                    "errors": errors,
                },
                status=400,
            )

        try:
            with transaction.atomic():
                order = Order.objects.create(
                    order_number=Order.generate_order_number(),
                    customer_reference=data.get('customer_reference', '').strip(),
                    notes=data.get('notes', '').strip(),
                )

                for prod, qty in validated_items:
                    OrderItem.objects.create(
                        order=order,
                        product=prod,
                        quantity=qty,
                        unit_length_snapshot=prod.length,
                        unit_width_snapshot=prod.width,
                        unit_height_snapshot=prod.height,
                        unit_weight_snapshot=prod.weight,
                    )

                # Run packaging evaluation
                allow_upright = bool(data.get('allow_upright_only', False))
                order, result, logs = evaluate_and_pack_order(order, allow_upright_only=allow_upright)

            return JsonResponse(
                {
                    "message": f"Order #{order.order_number} created and evaluated successfully.",
                    "order": serialize_order_detail(order),
                },
                status=201,
            )
        except Exception as exc:
            logger.exception("Error creating order: %s", exc)
            return JsonResponse(
                {"error": "Internal Server Error", "detail": f"Failed to create order: {str(exc)}"},
                status=500,
            )


class OrderDetailAPIView(View):
    """
    GET /api/orders/<str:order_id>/ - Retrieve order details and items
    """

    def get(self, request, order_id: str, *args, **kwargs):
        try:
            if order_id.isdigit():
                order = Order.objects.select_related('selected_box', 'packing_result').prefetch_related('items__product').get(id=int(order_id))
            else:
                order = Order.objects.select_related('selected_box', 'packing_result').prefetch_related('items__product').get(order_number=order_id)
            return JsonResponse({"order": serialize_order_detail(order)}, status=200)
        except Order.DoesNotExist:
            return JsonResponse(
                {"error": "Not Found", "detail": f"Order '{order_id}' does not exist."},
                status=404,
            )
        except Exception as exc:
            logger.exception("Error retrieving order '%s': %s", order_id, exc)
            return JsonResponse({"error": "Internal Server Error", "detail": "Failed to retrieve order."}, status=500)
