from django import forms
from .models import GCashTransaction, GCashSettings


class GCashTransactionForm(forms.ModelForm):
    class Meta:
        model  = GCashTransaction
        fields = ['txn_type', 'amount', 'service_fee', 'customer_name', 'reference_number', 'notes']
        widgets = {
            'txn_type':         forms.Select(attrs={'class': 'form-select'}),
            'amount':           forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01', 'id': 'id_amount'}),
            'service_fee':      forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'id': 'id_service_fee'}),
            'customer_name':    forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional'}),
            'reference_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional'}),
            'notes':            forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Optional notes'}),
        }

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is None or amount <= 0:
            raise forms.ValidationError('Amount must be greater than zero.')
        return amount

    def clean_service_fee(self):
        fee = self.cleaned_data.get('service_fee')
        if fee is None or fee < 0:
            raise forms.ValidationError('Service fee cannot be negative.')
        return fee


class GCashSettingsForm(forms.ModelForm):
    class Meta:
        model  = GCashSettings
        fields = ['fee_per_1000', 'apply_rounding']
        widgets = {
            'fee_per_1000':   forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'apply_rounding': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'fee_per_1000':   'Fee per \u20b11,000',
            'apply_rounding': 'Apply rounding to computed fee',
        }
