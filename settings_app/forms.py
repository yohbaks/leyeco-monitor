from django import forms
from .models import SystemSettings


class SystemSettingsForm(forms.ModelForm):
    class Meta:
        model = SystemSettings
        fields = [
            'business_name',
            'branch_address',
            'receipt_footer',
            'service_fee',
            'email_enabled',
            'smtp_host',
            'smtp_port',
            'smtp_use_tls',
            'smtp_username',
            'smtp_password',
            'email_from',
            'admin_email',
            'notify_void_request',
            'notify_eod_shortage',
            'notify_daily_summary',
            'notify_new_user',
        ]
        widgets = {
            'business_name'  : forms.TextInput(attrs={'class': 'form-control'}),
            'branch_address' : forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Brgy. Poblacion, Leyte'}),
            'receipt_footer' : forms.TextInput(attrs={'class': 'form-control'}),
            'service_fee'    : forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'email_enabled'  : forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'smtp_host'      : forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'smtp.gmail.com'}),
            'smtp_port'      : forms.NumberInput(attrs={'class': 'form-control'}),
            'smtp_use_tls'   : forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'smtp_username'  : forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'youraddress@gmail.com'}),
            'smtp_password'  : forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Gmail App Password (16 characters)'}, render_value=True),
            'email_from'     : forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'LEYECO Monitor <youraddress@gmail.com>'}),
            'admin_email'    : forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'admin@email.com, manager@email.com'}),
            'notify_void_request' : forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notify_eod_shortage' : forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notify_daily_summary': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notify_new_user'     : forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'smtp_password' : 'Gmail App Password',
            'email_from'    : 'From Address',
            'admin_email'   : 'Notify These Emails',
            'smtp_use_tls'  : 'Use TLS (recommended)',
        }
        help_texts = {
            'admin_email'   : 'Separate multiple addresses with commas.',
            'smtp_password' : 'Use a Gmail App Password, not your regular Gmail password.',
            'service_fee'   : 'Amount charged per transaction on top of the bill.',
            'email_from'    : 'Optional. Defaults to smtp_username if left blank.',
        }


class TestEmailForm(forms.Form):
    test_recipient = forms.EmailField(
        label='Send test email to',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter any email address to test',
        })
    )
