from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Avg, F, Max, Min, ProtectedError, Q
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView
from .forms import BoxForm, ProductForm
from .models import Box, Product


class ProductListView(ListView):
    """
    Searchable, filterable, and paginated product master data changelist.
    """
    model = Product
    template_name = 'catalog/product_list.html'
    context_object_name = 'products'
    paginate_by = 10

    def get_queryset(self):
        qs = super().get_queryset()
        query = self.request.GET.get('q', '').strip()
        sort = self.request.GET.get('sort', 'sku')

        if query:
            qs = qs.filter(Q(sku__icontains=query) | Q(name__icontains=query))

        sort_mapping = {
            'sku': 'sku',
            '-sku': '-sku',
            'name': 'name',
            '-name': '-name',
            'weight': 'weight',
            '-weight': '-weight',
            'newest': '-created_at',
            'oldest': 'created_at',
        }

        if sort == 'volume':
            qs = qs.annotate(calc_volume=F('length') * F('width') * F('height')).order_by('-calc_volume')
        elif sort == '-volume':
            qs = qs.annotate(calc_volume=F('length') * F('width') * F('height')).order_by('calc_volume')
        elif sort in sort_mapping:
            qs = qs.order_by(sort_mapping[sort])
        else:
            qs = qs.order_by('sku')

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '').strip()
        context['current_sort'] = self.request.GET.get('sort', 'sku')
        context['total_catalog_count'] = Product.objects.count()
        context['catalog_stats'] = Product.objects.aggregate(
            min_weight=Min('weight'),
            max_weight=Max('weight'),
            avg_weight=Avg('weight'),
        )
        context['add_form'] = ProductForm()
        return context


class ProductCreateView(LoginRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'catalog/product_form.html'
    success_url = reverse_lazy('catalog:product_list')

    def form_valid(self, form):
        messages.success(self.request, f"Product SKU '{form.instance.sku}' created successfully.")
        return super().form_valid(form)


class ProductUpdateView(LoginRequiredMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'catalog/product_form.html'
    success_url = reverse_lazy('catalog:product_list')

    def form_valid(self, form):
        messages.success(self.request, f"Product '{form.instance.sku}' updated successfully.")
        return super().form_valid(form)


class ProductDeleteView(LoginRequiredMixin, DeleteView):
    """
    Safely deletes a product, catching referential integrity ProtectedError
    if the SKU is linked to existing order items.
    """
    model = Product
    success_url = reverse_lazy('catalog:product_list')

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        sku = self.object.sku
        try:
            self.object.delete()
            messages.success(request, f"Product '{sku}' was successfully deleted.")
        except ProtectedError:
            messages.error(
                request,
                f"Cannot delete Product '{sku}' because it is linked to historical customer orders. "
                f"Referential integrity requires preserving SKU specifications for auditability.",
            )
        return redirect(self.success_url)


class ShippingBoxListView(ListView):
    """
    Searchable, filterable, and paginated shipping box inventory.
    """
    model = Box
    template_name = 'catalog/box_list.html'
    context_object_name = 'boxes'
    paginate_by = 10

    def get_queryset(self):
        qs = super().get_queryset()
        query = self.request.GET.get('q', '').strip()
        status_filter = self.request.GET.get('status', 'all')
        sort = self.request.GET.get('sort', 'cost')

        if query:
            qs = qs.filter(name__icontains=query)

        if status_filter == 'active':
            qs = qs.filter(is_active=True)
        elif status_filter == 'inactive':
            qs = qs.filter(is_active=False)

        sort_mapping = {
            'cost': 'packaging_cost',
            '-cost': '-packaging_cost',
            'name': 'name',
            '-name': '-name',
            'weight': 'max_weight_capacity',
            '-weight': '-max_weight_capacity',
            'newest': '-created_at',
        }

        if sort == 'volume':
            qs = qs.annotate(
                calc_volume=F('internal_length') * F('internal_width') * F('internal_height')
            ).order_by('-calc_volume')
        elif sort == '-volume':
            qs = qs.annotate(
                calc_volume=F('internal_length') * F('internal_width') * F('internal_height')
            ).order_by('calc_volume')
        elif sort in sort_mapping:
            qs = qs.order_by(sort_mapping[sort])
        else:
            qs = qs.order_by('packaging_cost')

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '').strip()
        context['current_status'] = self.request.GET.get('status', 'all')
        context['current_sort'] = self.request.GET.get('sort', 'cost')
        context['total_box_count'] = Box.objects.count()
        context['active_box_count'] = Box.objects.filter(is_active=True).count()
        context['box_stats'] = Box.objects.aggregate(
            min_cost=Min('packaging_cost'),
            max_capacity=Max('max_weight_capacity'),
            avg_cost=Avg('packaging_cost'),
        )
        context['add_form'] = BoxForm()
        return context


class ShippingBoxCreateView(LoginRequiredMixin, CreateView):
    model = Box
    form_class = BoxForm
    template_name = 'catalog/box_form.html'
    success_url = reverse_lazy('catalog:box_list')

    def form_valid(self, form):
        messages.success(self.request, f"Shipping Box '{form.instance.name}' added successfully.")
        return super().form_valid(form)


class ShippingBoxUpdateView(LoginRequiredMixin, UpdateView):
    model = Box
    form_class = BoxForm
    template_name = 'catalog/box_form.html'
    success_url = reverse_lazy('catalog:box_list')

    def form_valid(self, form):
        messages.success(self.request, f"Shipping Box '{form.instance.name}' updated successfully.")
        return super().form_valid(form)


class ShippingBoxDeleteView(LoginRequiredMixin, DeleteView):
    """
    Safely deletes a shipping box container profile.
    """
    model = Box
    success_url = reverse_lazy('catalog:box_list')

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        name = self.object.name
        try:
            self.object.delete()
            messages.success(request, f"Shipping Box '{name}' was successfully deleted.")
        except ProtectedError:
            messages.error(
                request,
                f"Cannot delete Box '{name}' because it is linked to historical dispatch records.",
            )
        return redirect(self.success_url)


class ShippingBoxToggleActiveView(LoginRequiredMixin, UpdateView):
    """
    Quickly toggles the active/inactive status of a box.
    """
    model = Box

    def post(self, request, *args, **kwargs):
        box = self.get_object()
        box.is_active = not box.is_active
        box.save(update_fields=['is_active', 'updated_at'])
        status_text = "activated and will be considered by the 3D packing engine" if box.is_active else "deactivated and excluded from future recommendations"
        messages.info(request, f"Shipping Box '{box.name}' has been {status_text}.")
        return redirect('catalog:box_list')


# Aliases
BoxListView = ShippingBoxListView
BoxCreateView = ShippingBoxCreateView
BoxUpdateView = ShippingBoxUpdateView
BoxDeleteView = ShippingBoxDeleteView
BoxToggleActiveView = ShippingBoxToggleActiveView
