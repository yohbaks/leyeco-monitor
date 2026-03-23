from decimal import Decimal
from django import forms
from .models import Payment, CashDenomination, DENOMINATION_CHOICES


class PaymentForm(forms.ModelForm):
    # Cash denomination fields (not model fields — handled in view)
    denom_1000 = forms.IntegerField(min_value=0, initial=0, required=False, label='₱1,000')
    denom_500  = forms.IntegerField(min_value=0, initial=0, required=False, label='₱500')
    denom_200  = forms.IntegerField(min_value=0, initial=0, required=False, label='₱200')
    denom_100  = forms.IntegerField(min_value=0, initial=0, required=False, label='₱100')
    denom_50   = forms.IntegerField(min_value=0, initial=0, required=False, label='₱50')
    denom_20   = forms.IntegerField(min_value=0, initial=0, required=False, label='₱20')
    denom_10   = forms.IntegerField(min_value=0, initial=0, required=False, label='₱10')
    denom_5    = forms.IntegerField(min_value=0, initial=0, required=False, label='₱5')
    denom_1    = forms.IntegerField(min_value=0, initial=0, required=False, label='₱1')

    class Meta:
        model = Payment
        fields = [
            'biller_name',
            'biller_account_number',
            'bill_amount',
            'cash_received',
            'leyeco_reference',
            'notes',
        ]
        widgets = {
            'biller_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Juan dela Cruz',
                'autofocus': True,
            }),
            'biller_account_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. 0123456789',
            }),
            'bill_amount': forms.NumberInput(attrs={
                'class': 'form-control bill-amount-input',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '1',
            }),
            'cash_received': forms.NumberInput(attrs={
                'class': 'form-control cash-received-input',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '1',
                'readonly': 'readonly',
            }),
            'leyeco_reference': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Official LEYECO reference number',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Optional notes...',
            }),
        }
        labels = {
            'bill_amount': 'Bill Amount (₱)',
            'cash_received': 'Cash Received (₱)',
            'leyeco_reference': 'LEYECO Reference No.',
            'notes': 'Notes (Optional)',
        }

    def clean(self):
        cleaned_data = super().clean()
        bill_amount = cleaned_data.get('bill_amount')
        cash_received = cleaned_data.get('cash_received')

        if bill_amount and cash_received:
            total_due = bill_amount + Decimal('10.00')
            if cash_received < total_due:
                raise forms.ValidationError(
                    f'Cash received (₱{cash_received:,.2f}) is less than the total due '
                    f'(₱{total_due:,.2f}). Please collect the correct amount.'
                )

        # Validate denomination total matches cash_received
        denom_map = {
            1000: cleaned_data.get('denom_1000') or 0,
            500:  cleaned_data.get('denom_500')  or 0,
            200:  cleaned_data.get('denom_200')  or 0,
            100:  cleaned_data.get('denom_100')  or 0,
            50:   cleaned_data.get('denom_50')   or 0,
            20:   cleaned_data.get('denom_20')   or 0,
            10:   cleaned_data.get('denom_10')   or 0,
            5:    cleaned_data.get('denom_5')    or 0,
            1:    cleaned_data.get('denom_1')    or 0,
        }
        denom_total = sum(k * v for k, v in denom_map.items())

        if cash_received and Decimal(str(denom_total)) != cash_received:
            raise forms.ValidationError(
                f'Denomination total (₱{denom_total:,.2f}) does not match '
                f'cash received (₱{cash_received:,.2f}). Please recheck the denominations.'
            )

        return cleaned_data

    def get_denominations(self):
        """Return denomination dict for saving after form validation."""
        cd = self.cleaned_data
        return {
            1000: cd.get('denom_1000') or 0,
            500:  cd.get('denom_500')  or 0,
            200:  cd.get('denom_200')  or 0,
            100:  cd.get('denom_100')  or 0,
            50:   cd.get('denom_50')   or 0,
            20:   cd.get('denom_20')   or 0,
            10:   cd.get('denom_10')   or 0,
            5:    cd.get('denom_5')    or 0,
            1:    cd.get('denom_1')    or 0,
        }


class VoidRequestForm(forms.Form):
    void_reason = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        label='Reason for void request',
        min_length=10,
    )
