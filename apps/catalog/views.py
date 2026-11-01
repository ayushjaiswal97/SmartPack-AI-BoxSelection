from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView
from .forms import ProductForm, ShippingBoxForm
from .models import Product, ShippingBox


class ProductListView(ListView):
    model = Product
    template_name = 'catalog/product_list.html'
    context_object_name = 'products'
    paginate_by = 20


class ProductCreateView(LoginRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'catalog/product_form.html'
    success_url = reverse_lazy('catalog:product_list')

    def form_valid(self, form):
        messages.success(self.request, f"Product '{form.instance.sku}' created successfully.")
        return super().form_valid(form)


class ProductUpdateView(LoginRequiredMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'catalog/product_form.html'
    success_url = reverse_lazy('catalog:product_list')

    def form_valid(self, form):
        messages.success(self.request, f"Product '{form.instance.sku}' updated successfully.")
        return super().form_valid(form)


class ShippingBoxListView(ListView):
    model = ShippingBox
    template_name = 'catalog/box_list.html'
    context_object_name = 'boxes'


class ShippingBoxCreateView(LoginRequiredMixin, CreateView):
    model = ShippingBox
    form_class = ShippingBoxForm
    template_name = 'catalog/box_form.html'
    success_url = reverse_lazy('catalog:box_list')

    def form_valid(self, form):
        messages.success(self.request, f"Shipping Box '{form.instance.name}' added successfully.")
        return super().form_valid(form)


class ShippingBoxUpdateView(LoginRequiredMixin, UpdateView):
    model = ShippingBox
    form_class = ShippingBoxForm
    template_name = 'catalog/box_form.html'
    success_url = reverse_lazy('catalog:box_list')

    def form_valid(self, form):
        messages.success(self.request, f"Shipping Box '{form.instance.name}' updated successfully.")
        return super().form_valid(form)
