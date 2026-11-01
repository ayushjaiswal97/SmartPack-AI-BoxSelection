import json
from decimal import Decimal
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import DetailView, ListView, View
from apps.catalog.models import Box, Product
from .forms import OrderForm, OrderItemFormSet
from .models import Order, OrderItem
from .services import evaluate_and_pack_order


class DashboardView(View):
    """
    Main operations console displaying live warehouse KPIs,
    active dispatch queue, packaging materials summary, and quick action shortcuts.
    """
    template_name = 'orders/dashboard.html'

    def get(self, request, *args, **kwargs):
        total_products = Product.objects.count()
        total_boxes = Box.objects.count()
        active_boxes = Box.objects.filter(is_active=True).count()
        total_orders = Order.objects.count()

        orders_awaiting = Order.objects.filter(status=Order.Status.DRAFT).count()
        orders_evaluated = Order.objects.filter(status=Order.Status.EVALUATED).count()
        orders_packed = Order.objects.filter(status=Order.Status.PACKED).count()
        orders_failed = Order.objects.filter(status=Order.Status.FAILED).count()

        recent_orders = (
            Order.objects.select_related('selected_box', 'packing_result')
            .prefetch_related('items__product')
            .order_by('-created_at')[:8]
        )
        active_boxes_sample = Box.objects.filter(is_active=True).order_by('packaging_cost')[:6]

        context = {
            'total_products': total_products,
            'total_boxes': total_boxes,
            'active_boxes': active_boxes,
            'total_orders': total_orders,
            'orders_awaiting': orders_awaiting,
            'orders_evaluated': orders_evaluated,
            'orders_packed': orders_packed,
            'orders_failed': orders_failed,
            'recent_orders': recent_orders,
            'active_boxes_sample': active_boxes_sample,
        }
        return render(request, self.template_name, context)


class OrderSimulatorView(View):
    """
    Main interactive box selection simulator where warehouse operators
    can build multi-item orders and instantly get the lowest-cost box recommendation.
    """
    template_name = 'orders/simulator.html'

    def get(self, request, *args, **kwargs):
        order_form = OrderForm()
        formset = OrderItemFormSet(queryset=OrderItem.objects.none())
        products = Product.objects.all().order_by('name')
        existing_orders = (
            Order.objects.select_related('selected_box')
            .prefetch_related('items__product')
            .order_by('-created_at')[:25]
        )

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
                'existing_orders': existing_orders,
                'product_data_json': json.dumps(product_data),
            },
        )

    def post(self, request, *args, **kwargs):
        order_form = OrderForm(request.POST)
        formset = OrderItemFormSet(request.POST)
        products = Product.objects.all().order_by('name')

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
                        customer_reference=request.POST.get('customer_reference', ''),
                        notes=order_form.cleaned_data.get('notes', ''),
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

                if order.status == Order.Status.EVALUATED:
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
        existing_orders = (
            Order.objects.select_related('selected_box')
            .prefetch_related('items__product')
            .order_by('-created_at')[:25]
        )
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
                'existing_orders': existing_orders,
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
        boxes = Box.objects.filter(is_active=True).order_by('packaging_cost', 'name')

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
    """
    Searchable, filterable, and paginated order dispatch changelist and recommendation audit history.
    """
    model = Order
    template_name = 'orders/order_list.html'
    context_object_name = 'orders'
    paginate_by = 15

    def get_queryset(self):
        qs = (
            Order.objects.select_related('selected_box', 'packing_result')
            .prefetch_related('items__product')
        )
        query = self.request.GET.get('q', '').strip()
        status_filter = self.request.GET.get('status', 'all')
        sort = self.request.GET.get('sort', 'newest')

        if query:
            qs = qs.filter(
                Q(order_number__icontains=query) |
                Q(customer_reference__icontains=query)
            )

        if status_filter in [s.value for s in Order.Status]:
            qs = qs.filter(status=status_filter)

        sort_mapping = {
            'newest': '-created_at',
            'oldest': 'created_at',
            'number': 'order_number',
            'weight': '-total_order_weight',
            'cost': '-packaging_cost',
        }
        return qs.order_by(sort_mapping.get(sort, '-created_at'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '').strip()
        context['current_status'] = self.request.GET.get('status', 'all')
        context['current_sort'] = self.request.GET.get('sort', 'newest')
        
        # Live status summary counts
        context['count_all'] = Order.objects.count()
        context['count_draft'] = Order.objects.filter(status=Order.Status.DRAFT).count()
        context['count_evaluated'] = Order.objects.filter(status=Order.Status.EVALUATED).count()
        context['count_packed'] = Order.objects.filter(status=Order.Status.PACKED).count()
        context['count_failed'] = Order.objects.filter(status=Order.Status.FAILED).count()
        return context


class OrderDetailView(DetailView):
    """
    Detailed operational order view showing customer reference, item manifest,
    bounding properties, and packaging evaluation summary.
    """
    model = Order
    template_name = 'orders/order_detail.html'
    context_object_name = 'order'
    slug_field = 'order_number'
    slug_url_kwarg = 'order_number'

    def get_queryset(self):
        return (
            Order.objects.select_related('selected_box', 'packing_result')
            .prefetch_related('items__product')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order = self.object
        items = list(order.items.select_related('product').all())
        context['order_items'] = items
        context['total_pieces'] = sum(item.quantity for item in items)
        
        # Check if packing result exists
        packing_result = getattr(order, 'packing_result', None)
        context['packing_result'] = packing_result
        if packing_result and packing_result.placements_manifest:
            context['placements_manifest'] = packing_result.placements_manifest
            context['evaluated_boxes_summary'] = packing_result.evaluated_boxes_summary
        else:
            context['placements_manifest'] = []
            context['evaluated_boxes_summary'] = []

        return context


class RecommendationHistoryView(ListView):
    """
    Dedicated historical audit log of all packaging recommendations,
    recording selected container, recommendation date/time, packaging cost,
    and spatial utilization metrics.
    """
    model = Order
    template_name = 'orders/history_list.html'
    context_object_name = 'evaluations'
    paginate_by = 15

    def get_queryset(self):
        qs = (
            Order.objects.filter(status__in=[Order.Status.EVALUATED, Order.Status.PACKED, Order.Status.FAILED])
            .select_related('selected_box', 'packing_result')
            .prefetch_related('items__product')
            .order_by('-updated_at')
        )
        query = self.request.GET.get('q', '').strip()
        status_filter = self.request.GET.get('status', 'all')
        if query:
            qs = qs.filter(
                Q(order_number__icontains=query) |
                Q(customer_reference__icontains=query) |
                Q(selected_box__name__icontains=query)
            )
        if status_filter in ['EVALUATED', 'PACKED', 'FAILED']:
            qs = qs.filter(status=status_filter)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '').strip()
        context['current_status'] = self.request.GET.get('status', 'all')
        context['total_evaluations'] = Order.objects.filter(
            status__in=[Order.Status.EVALUATED, Order.Status.PACKED, Order.Status.FAILED]
        ).count()
        context['feasible_count'] = Order.objects.filter(
            status__in=[Order.Status.EVALUATED, Order.Status.PACKED]
        ).count()
        context['infeasible_count'] = Order.objects.filter(
            status=Order.Status.FAILED
        ).count()
        return context
