import logging
from django.db import DatabaseError
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from apps.orders.exceptions import EmptyOrderError, OrderNotFoundError
from apps.orders.services import PackagingService

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
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

