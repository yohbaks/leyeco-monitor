from django import forms
from .models import Category, Product, Sale


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name', 'category', 'sku', 'size', 'color',
            'cost_price', 'selling_price', 'stock_quantity', 'is_active',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'sku': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. RTW-001'}),
            'size': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. S, M, L, XL, 32'}),
            'color': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Blue, Red'}),
            'cost_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'selling_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'stock_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        cleaned = super().clean()
        cost = cleaned.get('cost_price')
        price = cleaned.get('selling_price')
        if cost is not None and price is not None and price < cost:
            self.add_error('selling_price', 'Selling price should not be lower than cost price.')
        return cleaned


class SaleHeaderForm(forms.ModelForm):
    class Meta:
        model = Sale
        fields = ['customer_name', 'discount_amount', 'cash_received', 'notes']
        widgets = {
            'customer_name': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Leave blank for walk-in',
            }),
            'discount_amount': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01', 'min': '0', 'value': '0.00',
                'id': 'id_discount',
            }),
            'cash_received': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01', 'min': '0',
                'id': 'id_cash_received',
            }),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def clean_cash_received(self):
        cash = self.cleaned_data.get('cash_received')
        if cash is not None and cash < 0:
            raise forms.ValidationError('Cash received cannot be negative.')
        return cash


class VoidSaleForm(forms.Form):
    void_reason = forms.CharField(
        label='Reason for void',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        min_length=5,
    )


class StockAdjustForm(forms.Form):
    adjustment = forms.IntegerField(
        label='Quantity adjustment',
        help_text='Use positive to add stock, negative to reduce.',
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )
    reason = forms.CharField(
        label='Reason',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Restock, Damage, Return'}),
    )
