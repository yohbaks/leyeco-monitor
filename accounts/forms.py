from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth import get_user_model

User = get_user_model()


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Username',
            'autofocus': True,
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Password',
        })
    )


class UserCreateForm(forms.ModelForm):
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Set password'}),
        min_length=6,
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Repeat password'}),
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'role', 'branch', 'employee_id']
        widgets = {
            'username':    forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. teller3'}),
            'first_name':  forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First name'}),
            'last_name':   forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last name'}),
            'email':       forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email (optional)'}),
            'role':        forms.Select(attrs={'class': 'form-select'}),
            'branch':      forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Main Branch'}),
            'employee_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Employee ID (optional)'}),
        }

    def clean(self):
        cd = super().clean()
        p1 = cd.get('password1')
        p2 = cd.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('Passwords do not match.')
        return cd

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user


class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'role', 'branch', 'employee_id', 'is_active', 'force_password_change']
        widgets = {
            'first_name':  forms.TextInput(attrs={'class': 'form-control'}),
            'last_name':   forms.TextInput(attrs={'class': 'form-control'}),
            'email':       forms.EmailInput(attrs={'class': 'form-control'}),
            'role':        forms.Select(attrs={'class': 'form-select'}),
            'branch':      forms.TextInput(attrs={'class': 'form-control'}),
            'employee_id': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active':   forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'force_password_change': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'is_active': 'Account active (uncheck to deactivate)',
        }


class ResetPasswordForm(forms.Form):
    new_password1 = forms.CharField(
        label='New Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'New password'}),
        min_length=6,
    )
    new_password2 = forms.CharField(
        label='Confirm New Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Repeat new password'}),
    )

    def clean(self):
        cd = super().clean()
        p1 = cd.get('new_password1')
        p2 = cd.get('new_password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('Passwords do not match.')
        return cd


class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'
