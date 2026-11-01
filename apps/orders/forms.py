from django import forms
from django.forms import inlineformset_factory
from apps.catalog.models import Product
from .models import Order, OrderItem


class OrderForm(forms.ModelForm):
    allow_upright_only = forms.BooleanField(
        required=False,
        initial=False,
        label="Strict Upright Packing Only",
        help_text="If checked, prevents tilting items on their side (useful for liquids/fragile goods).",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )

    class Meta:
        model = Order
        fields = ['customer_reference', 'notes']
        widgets = {
            'customer_reference': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Customer name or reference ID (e.g. CUST-8831)...',
                }
            ),
            'notes': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 2,
                    'placeholder': 'Optional internal warehouse packaging instructions...',
                }
            ),
        }


class OrderItemForm(forms.ModelForm):
    product = forms.ModelChoiceField(
        queryset=Product.objects.all().order_by('name'),
        widget=forms.Select(attrs={'class': 'form-select product-selector'}),
        empty_label="-- Select Product SKU --",
    )
    quantity = forms.IntegerField(
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={'class': 'form-control item-quantity', 'min': '1', 'value': '1'}),
    )

    class Meta:
        model = OrderItem
        fields = ['product', 'quantity']


OrderItemFormSet = inlineformset_factory(
    Order,
    OrderItem,
    form=OrderItemForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True,
)
