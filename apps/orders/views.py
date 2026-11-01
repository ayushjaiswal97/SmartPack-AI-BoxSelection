import json
from decimal import Decimal
from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import DetailView, ListView, View
from apps.catalog.models import Product, ShippingBox
from .forms import OrderForm, OrderItemFormSet
from .models import Order, OrderItem
from .services import evaluate_and_pack_order


class OrderSimulatorView(View):
    """
    Main interactive box selection simulator where warehouse operators
    can build multi-item orders and instantly get the lowest-cost box recommendation.
    """
    template_name = 'orders/simulator.html'

    def get(self, request, *args, **kwargs):
        order_form = OrderForm()
        formset = OrderItemFormSet(queryset=OrderItem.objects.none())
        products = Product.objects.filter(is_active=True).order_by('name')

        # Serialize product catalog for frontend instant dimension preview
        product_data = {
            p.id: {
                "sku": p.sku,
                "name": p.name,
                "length": float(p.length),
                "width": float(p.width),
                "height": float(p.height),
                "weight": float(p.weight),
            }
            for p in products
        }

        return render(
            request,
            self.template_name,
            {
                'order_form': order_form,
                'formset': formset,
                'products': products,
                'product_data_json': json.dumps(product_data),
            },
        )

    def post(self, request, *args, **kwargs):
        order_form = OrderForm(request.POST)
        formset = OrderItemFormSet(request.POST)
        products = Product.objects.filter(is_active=True).order_by('name')

        if order_form.is_valid() and formset.is_valid():
            cleaned_items = [
                f.cleaned_data for f in formset.forms
                if f.cleaned_data and not f.cleaned_data.get('DELETE', False) and f.cleaned_data.get('product')
            ]

            if not cleaned_items:
                messages.error(request, "Please add at least one product with a quantity of 1 or more.")
                return self.render_with_context(request, order_form, formset, products)

            try:
                with transaction.atomic():
                    order = Order.objects.create(
                        order_number=Order.generate_order_number(),
                        notes=order_form.cleaned_data.get('notes', ''),
                        created_by=request.user if request.user.is_authenticated else None,
                    )

                    for item_data in cleaned_items:
                        prod = item_data['product']
                        qty = item_data['quantity']
                        OrderItem.objects.create(
                            order=order,
                            product=prod,
                            quantity=qty,
                        )

                    allow_upright = order_form.cleaned_data.get('allow_upright_only', False)
                    order, result, logs = evaluate_and_pack_order(order, allow_upright_only=allow_upright)

                if order.status == Order.STATUS_EVALUATED:
                    messages.success(
                        request,
                        f"Optimal box selected: '{order.selected_box.name}' at ${order.packaging_cost}."
                    )
                else:
                    messages.warning(
                        request,
                        "Order packing infeasible: No single box can fit all items in the order."
                    )

                return redirect('orders:recommendation', order_number=order.order_number)

            except Exception as e:
                messages.error(request, f"An error occurred during evaluation: {str(e)}")
                return self.render_with_context(request, order_form, formset, products)

        else:
            messages.error(request, "Please correct the errors in the form below.")
            return self.render_with_context(request, order_form, formset, products)

    def render_with_context(self, request, order_form, formset, products):
        product_data = {
            p.id: {
                "sku": p.sku,
                "name": p.name,
                "length": float(p.length),
                "width": float(p.width),
                "height": float(p.height),
                "weight": float(p.weight),
            }
            for p in products
        }
        return render(
            request,
            self.template_name,
            {
                'order_form': order_form,
                'formset': formset,
                'products': products,
                'product_data_json': json.dumps(product_data),
            },
        )


class OrderRecommendationView(DetailView):
    """
    Displays the recommended shipping box, 3D placement manifest,
    space/weight utilization, and comparison against all candidate boxes.
    """
    model = Order
    template_name = 'orders/recommendation.html'
    context_object_name = 'order'
    slug_field = 'order_number'
    slug_url_kwarg = 'order_number'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order = self.object
        boxes = ShippingBox.objects.filter(is_active=True).order_by('packaging_cost', 'name')
        
        # Calculate comparison matrix for all active boxes
        comparison = []
        for box in boxes:
            wt_ok = order.total_weight <= box.max_weight_capacity
            vol_ok = order.total_volume <= box.internal_volume
            is_selected = (order.selected_box_id == box.id)
            comparison.append({
                'box': box,
                'is_selected': is_selected,
                'weight_feasible': wt_ok,
                'volume_feasible': vol_ok,
                'cost': box.packaging_cost,
            })

        context['comparison_boxes'] = comparison
        context['items'] = order.items.select_related('product').all()
        try:
            context['packing_result'] = order.packing_result
            context['placed_items_json'] = json.dumps(order.packing_result.placed_items_manifest)
        except Exception:
            context['packing_result'] = None
            context['placed_items_json'] = '[]'
        return context


class OrderListView(ListView):
    model = Order
    template_name = 'orders/order_list.html'
    context_object_name = 'orders'
    paginate_by = 25


class OrderDetailView(DetailView):
    model = Order
    template_name = 'orders/order_detail.html'
    context_object_name = 'order'
    slug_field = 'order_number'
    slug_url_kwarg = 'order_number'
