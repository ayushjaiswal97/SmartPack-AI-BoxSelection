# apps/catalog/forms.py
from django import forms
from .models import Product, ShippingBox


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['sku', 'name', 'length', 'width', 'height', 'weight', 'is_active']
        widgets = {
            'sku': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. ELEC-PHN-01'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Smartphone Pro'}),
            'length': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'width': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'height': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'weight': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'min': '0.001'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ShippingBoxForm(forms.ModelForm):
    class Meta:
        model = ShippingBox
        fields = [
            'name',
            'internal_length',
            'internal_width',
            'internal_height',
            'max_weight_capacity',
            'packaging_cost',
            'is_active',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Standard Medium Box'}),
            'internal_length': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'internal_width': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'internal_height': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'max_weight_capacity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'min': '0.001'}),
            'packaging_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.00'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

