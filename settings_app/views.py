from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages

from .models import SystemSettings
from .forms import SystemSettingsForm, TestEmailForm
from .notifications import send_test_email
from audit.models import AuditLog


def _admin_required(view_func):
    from functools import wraps
    @wraps(view_func)
    @login_required
    def wrapped(request, *args, **kwargs):
        if not request.user.is_admin():
            messages.error(request, 'System settings are restricted to admins only.')
            return redirect('dashboard:index')
        return view_func(request, *args, **kwargs)
    return wrapped


@_admin_required
def settings_view(request):
    s = SystemSettings.get()

    if request.method == 'POST' and 'save_settings' in request.POST:
        form = SystemSettingsForm(request.POST, instance=s)
        test_form = TestEmailForm()
        if form.is_valid():
            form.save()
            AuditLog.objects.create(
                user=request.user,
                action='updated',
                ip_address=request.META.get('REMOTE_ADDR'),
                details={'action_type': 'settings_saved'}
            )
            messages.success(request, 'Settings saved successfully.')
            return redirect('settings_app:settings')
    elif request.method == 'POST' and 'send_test' in request.POST:
        form = SystemSettingsForm(instance=s)
        test_form = TestEmailForm(request.POST)
        if test_form.is_valid():
            recipient = test_form.cleaned_data['test_recipient']
            # Reload settings fresh in case they were just saved
            s = SystemSettings.get()
            ok = send_test_email(recipient, s)
            if ok:
                messages.success(request, f'Test email sent to {recipient}. Please check your inbox.')
            else:
                messages.error(
                    request,
                    'Failed to send test email. Please check your SMTP settings and make sure '
                    '"Enable Email Notifications" is turned on.'
                )
    else:
        form = SystemSettingsForm(instance=s)
        test_form = TestEmailForm()

    return render(request, 'settings_app/settings.html', {
        'form': form,
        'test_form': test_form,
        'settings': s,
    })
