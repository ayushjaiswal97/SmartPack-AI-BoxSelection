import json
import logging
from decimal import Decimal
from django.db import DatabaseError, IntegrityError
from django.db.models import ProtectedError
from django.http import JsonResponse
from django.views import View
from .forms import BoxForm, ProductForm
from .models import Box, Product

logger = logging.getLogger(__name__)


def serialize_product(product: Product) -> dict:
    return {
        "id": product.id,
        "sku": product.sku,
        "name": product.name,
        "length": float(product.length),
        "width": float(product.width),
        "height": float(product.height),
        "weight": float(product.weight),
        "volume": float(product.volume),
        "created_at": product.created_at.isoformat(),
        "updated_at": product.updated_at.isoformat(),
    }


def serialize_box(box: Box) -> dict:
    return {
        "id": box.id,
        "name": box.name,
        "internal_length": float(box.internal_length),
        "internal_width": float(box.internal_width),
        "internal_height": float(box.internal_height),
        "max_weight_capacity": float(box.max_weight_capacity),
        "packaging_cost": float(box.packaging_cost),
        "is_active": box.is_active,
        "internal_volume": float(box.internal_volume),
        "volume": float(box.volume),
        "created_at": box.created_at.isoformat(),
        "updated_at": box.updated_at.isoformat(),
    }


class ProductListCreateAPIView(View):
    """
    GET  /api/products/  - List products (supports ?q= query)
    POST /api/products/  - Create a new product
    """

    def get(self, request, *args, **kwargs):
        try:
            q = request.GET.get('q', '').strip()
            qs = Product.objects.all().order_by('sku')
            if q:
                from django.db.models import Q
                qs = qs.filter(Q(sku__icontains=q) | Q(name__icontains=q))
            products = [serialize_product(p) for p in qs]
            return JsonResponse({"products": products, "count": len(products)}, status=200)
        except Exception as exc:
            logger.exception("Error listing products: %s", exc)
            return JsonResponse({"error": "Internal Server Error", "detail": "Failed to fetch products."}, status=500)

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse(
                {"error": "Unauthorized", "detail": "Authentication required to create catalog products."},
                status=401,
            )

        try:
            if request.content_type == 'application/json':
                data = json.loads(request.body.decode('utf-8'))
            else:
                data = request.POST.dict()
        except json.JSONDecodeError:
            return JsonResponse({"error": "Bad Request", "detail": "Malformed JSON payload."}, status=400)

        form = ProductForm(data)
        if form.is_valid():
            product = form.save()
            return JsonResponse(
                {
                    "message": f"Product '{product.sku}' created successfully.",
                    "product": serialize_product(product),
                },
                status=201,
            )
        else:
            errors = {field: [e['message'] for e in err_list] for field, err_list in form.errors.get_json_data().items()}
            return JsonResponse(
                {
                    "error": "Validation Error",
                    "detail": "Please correct the input errors.",
                    "errors": errors,
                },
                status=400,
            )


class ProductDetailUpdateDeleteAPIView(View):
    """
    GET    /api/products/<int:pk>/  - Retrieve product details
    PUT    /api/products/<int:pk>/  - Update product
    DELETE /api/products/<int:pk>/  - Delete product (with 409 referential integrity check)
    """

    def get_object(self, pk: int):
        try:
            return Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            return None

    def get(self, request, pk: int, *args, **kwargs):
        product = self.get_object(pk)
        if not product:
            return JsonResponse({"error": "Not Found", "detail": f"Product with ID {pk} does not exist."}, status=404)
        return JsonResponse({"product": serialize_product(product)}, status=200)

    def put(self, request, pk: int, *args, **kwargs):
        return self.patch(request, pk, *args, **kwargs)

    def patch(self, request, pk: int, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse(
                {"error": "Unauthorized", "detail": "Authentication required to update catalog products."},
                status=401,
            )

        product = self.get_object(pk)
        if not product:
            return JsonResponse({"error": "Not Found", "detail": f"Product with ID {pk} does not exist."}, status=404)

        try:
            if request.content_type == 'application/json':
                data = json.loads(request.body.decode('utf-8'))
            else:
                data = request.POST.dict()
        except json.JSONDecodeError:
            return JsonResponse({"error": "Bad Request", "detail": "Malformed JSON payload."}, status=400)

        # Merge existing data for partial updates if needed
        merged_data = {
            'sku': data.get('sku', product.sku),
            'name': data.get('name', product.name),
            'length': data.get('length', product.length),
            'width': data.get('width', product.width),
            'height': data.get('height', product.height),
            'weight': data.get('weight', product.weight),
        }

        form = ProductForm(merged_data, instance=product)
        if form.is_valid():
            product = form.save()
            return JsonResponse(
                {
                    "message": f"Product '{product.sku}' updated successfully.",
                    "product": serialize_product(product),
                },
                status=200,
            )
        else:
            errors = {field: [e['message'] for e in err_list] for field, err_list in form.errors.get_json_data().items()}
            return JsonResponse(
                {
                    "error": "Validation Error",
                    "detail": "Please correct the input errors.",
                    "errors": errors,
                },
                status=400,
            )

    def delete(self, request, pk: int, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse(
                {"error": "Unauthorized", "detail": "Authentication required to delete catalog products."},
                status=401,
            )

        product = self.get_object(pk)
        if not product:
            return JsonResponse({"error": "Not Found", "detail": f"Product with ID {pk} does not exist."}, status=404)

        sku = product.sku
        try:
            product.delete()
            return JsonResponse(
                {"message": f"Product '{sku}' was successfully deleted."},
                status=200,
            )
        except ProtectedError:
            return JsonResponse(
                {
                    "error": "Conflict",
                    "detail": f"Cannot delete Product '{sku}' because it is linked to historical customer orders. Referential integrity requires preserving SKU specifications for auditability.",
                },
                status=409,
            )
        except Exception as exc:
            logger.exception("Error deleting product %s: %s", sku, exc)
            return JsonResponse({"error": "Internal Server Error", "detail": "Failed to delete product."}, status=500)


class BoxListCreateAPIView(View):
    """
    GET  /api/boxes/  - List shipping box containers
    POST /api/boxes/  - Register a new shipping box profile
    """

    def get(self, request, *args, **kwargs):
        try:
            qs = Box.objects.all().order_by('packaging_cost', 'name')
            status_param = request.GET.get('status')
            if status_param == 'active':
                qs = qs.filter(is_active=True)
            elif status_param == 'inactive':
                qs = qs.filter(is_active=False)

            boxes = [serialize_box(b) for b in qs]
            return JsonResponse({"boxes": boxes, "count": len(boxes)}, status=200)
        except Exception as exc:
            logger.exception("Error listing boxes: %s", exc)
            return JsonResponse({"error": "Internal Server Error", "detail": "Failed to fetch shipping boxes."}, status=500)

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse(
                {"error": "Unauthorized", "detail": "Authentication required to create box profiles."},
                status=401,
            )

        try:
            if request.content_type == 'application/json':
                data = json.loads(request.body.decode('utf-8'))
            else:
                data = request.POST.dict()
        except json.JSONDecodeError:
            return JsonResponse({"error": "Bad Request", "detail": "Malformed JSON payload."}, status=400)

        form = BoxForm(data)
        if form.is_valid():
            box = form.save()
            return JsonResponse(
                {
                    "message": f"Shipping Box '{box.name}' created successfully.",
                    "box": serialize_box(box),
                },
                status=201,
            )
        else:
            errors = {field: [e['message'] for e in err_list] for field, err_list in form.errors.get_json_data().items()}
            return JsonResponse(
                {
                    "error": "Validation Error",
                    "detail": "Please correct the input errors.",
                    "errors": errors,
                },
                status=400,
            )


class BoxDetailUpdateDeleteAPIView(View):
    """
    GET    /api/boxes/<int:pk>/  - Retrieve box details
    PUT    /api/boxes/<int:pk>/  - Update box profile
    DELETE /api/boxes/<int:pk>/  - Delete box profile
    """

    def get_object(self, pk: int):
        try:
            return Box.objects.get(pk=pk)
        except Box.DoesNotExist:
            return None

    def get(self, request, pk: int, *args, **kwargs):
        box = self.get_object(pk)
        if not box:
            return JsonResponse({"error": "Not Found", "detail": f"Box with ID {pk} does not exist."}, status=404)
        return JsonResponse({"box": serialize_box(box)}, status=200)

    def put(self, request, pk: int, *args, **kwargs):
        return self.patch(request, pk, *args, **kwargs)

    def patch(self, request, pk: int, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse(
                {"error": "Unauthorized", "detail": "Authentication required to update box profiles."},
                status=401,
            )

        box = self.get_object(pk)
        if not box:
            return JsonResponse({"error": "Not Found", "detail": f"Box with ID {pk} does not exist."}, status=404)

        try:
            if request.content_type == 'application/json':
                data = json.loads(request.body.decode('utf-8'))
            else:
                data = request.POST.dict()
        except json.JSONDecodeError:
            return JsonResponse({"error": "Bad Request", "detail": "Malformed JSON payload."}, status=400)

        merged_data = {
            'name': data.get('name', box.name),
            'internal_length': data.get('internal_length', box.internal_length),
            'internal_width': data.get('internal_width', box.internal_width),
            'internal_height': data.get('internal_height', box.internal_height),
            'max_weight_capacity': data.get('max_weight_capacity', box.max_weight_capacity),
            'packaging_cost': data.get('packaging_cost', box.packaging_cost),
            'is_active': data.get('is_active', box.is_active),
        }

        form = BoxForm(merged_data, instance=box)
        if form.is_valid():
            box = form.save()
            return JsonResponse(
                {
                    "message": f"Shipping Box '{box.name}' updated successfully.",
                    "box": serialize_box(box),
                },
                status=200,
            )
        else:
            errors = {field: [e['message'] for e in err_list] for field, err_list in form.errors.get_json_data().items()}
            return JsonResponse(
                {
                    "error": "Validation Error",
                    "detail": "Please correct the input errors.",
                    "errors": errors,
                },
                status=400,
            )

    def delete(self, request, pk: int, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse(
                {"error": "Unauthorized", "detail": "Authentication required to delete box profiles."},
                status=401,
            )

        box = self.get_object(pk)
        if not box:
            return JsonResponse({"error": "Not Found", "detail": f"Box with ID {pk} does not exist."}, status=404)

        name = box.name
        try:
            box.delete()
            return JsonResponse(
                {"message": f"Shipping Box '{name}' was successfully deleted."},
                status=200,
            )
        except ProtectedError:
            return JsonResponse(
                {
                    "error": "Conflict",
                    "detail": f"Cannot delete Box '{name}' because it is linked to historical dispatch records.",
                },
                status=409,
            )
        except Exception as exc:
            logger.exception("Error deleting box %s: %s", name, exc)
            return JsonResponse({"error": "Internal Server Error", "detail": "Failed to delete box."}, status=500)


class BoxToggleActiveAPIView(View):
    """
    POST /api/boxes/<int:pk>/toggle-active/
    """

    def post(self, request, pk: int, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse(
                {"error": "Unauthorized", "detail": "Authentication required."},
                status=401,
            )

        try:
            box = Box.objects.get(pk=pk)
        except Box.DoesNotExist:
            return JsonResponse({"error": "Not Found", "detail": f"Box with ID {pk} does not exist."}, status=404)

        box.is_active = not box.is_active
        box.save(update_fields=['is_active', 'updated_at'])
        state = "activated" if box.is_active else "deactivated"
        return JsonResponse(
            {
                "message": f"Shipping Box '{box.name}' {state} successfully.",
                "box": serialize_box(box),
            },
            status=200,
        )

