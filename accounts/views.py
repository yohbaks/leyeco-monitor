from django.contrib.auth import views as auth_views, update_session_auth_hash, get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Count, Sum, Max
from django.utils import timezone

from .forms import LoginForm, UserCreateForm, UserEditForm, ResetPasswordForm, CustomPasswordChangeForm
from audit.models import AuditLog

User = get_user_model()


def get_client_ip(request):
    x = request.META.get('HTTP_X_FORWARDED_FOR')
    return x.split(',')[0] if x else request.META.get('REMOTE_ADDR')


def _admin_required(view_func):
    from functools import wraps
    @wraps(view_func)
    @login_required
    def wrapped(request, *args, **kwargs):
        if not request.user.is_admin_or_manager():
            messages.error(request, 'Access denied.')
            return redirect('dashboard:index')
        return view_func(request, *args, **kwargs)
    return wrapped


# ── Login / Logout ────────────────────────────────────────────

class CustomLoginView(auth_views.LoginView):
    form_class = LoginForm
    template_name = 'accounts/login.html'

    def form_invalid(self, form):
        # axes handles attempt counting automatically via middleware
        return super().form_invalid(form)

    def form_valid(self, form):
        response = super().form_valid(form)
        AuditLog.objects.create(
            user=self.request.user,
            action='login',
            ip_address=get_client_ip(self.request),
            details={'username': self.request.user.username}
        )
        return response


class CustomLogoutView(auth_views.LogoutView):
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            AuditLog.objects.create(
                user=request.user,
                action='logout',
                ip_address=get_client_ip(request),
                details={}
            )
        return super().dispatch(request, *args, **kwargs)


# ── Profile + Change Password ─────────────────────────────────

@login_required
def force_password_check(request):
    """Redirect users who must change their password before doing anything else."""
    if request.user.is_authenticated and request.user.force_password_change:
        if request.path != '/accounts/password/' and not request.path.startswith('/accounts/logout'):
            return True
    return False


@login_required
def profile(request):
    from transactions.models import Payment
    from django.db.models import Count, Sum
    stats = Payment.objects.filter(
        teller=request.user, status='completed'
    ).aggregate(
        total_txns=Count('id'),
        total_collected=Sum('total_due'),
        total_fees=Sum('service_fee'),
    )
    recent = Payment.objects.filter(teller=request.user).order_by('-created_at')[:10]
    context = {
        'stats': stats,
        'recent': recent,
    }
    return render(request, 'accounts/profile.html', context)


@login_required
def change_password(request):
    if request.method == 'POST':
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, form.user)
            AuditLog.objects.create(
                user=request.user,
                action='updated',
                ip_address=get_client_ip(request),
                details={'action_type': 'password_changed'}
            )
            # Clear force_password_change flag if set
            if request.user.force_password_change:
                request.user.force_password_change = False
                request.user.save(update_fields=['force_password_change'])
            messages.success(request, 'Password changed successfully.')
            return redirect('accounts:profile')
    else:
        form = CustomPasswordChangeForm(request.user)
    return render(request, 'accounts/change_password.html', {'form': form})


# ── User Management ───────────────────────────────────────────

@_admin_required
def user_list(request):
    from transactions.models import Payment
    users = User.objects.annotate(
        txn_count=Count('payments'),
        last_login_ts=Max('last_login'),
    ).order_by('role', 'first_name', 'username')

    context = {'users': users}
    return render(request, 'accounts/management/list.html', context)


@_admin_required
def user_create(request):
    if request.method == 'POST':
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            AuditLog.objects.create(
                user=request.user,
                action='updated',
                ip_address=get_client_ip(request),
                details={'action_type': 'user_created', 'new_user': user.username}
            )
            # Welcome email
            try:
                from settings_app.notifications import send_welcome_email
                plain_pw = form.cleaned_data.get('password1', '')
                send_welcome_email(user, plain_pw)
            except Exception:
                pass
            messages.success(request, f'User "{user.username}" created successfully.')
            return redirect('accounts:user_list')
    else:
        form = UserCreateForm(initial={'branch': 'Main Branch'})
    return render(request, 'accounts/management/create.html', {'form': form})


@_admin_required
def user_edit(request, pk):
    target = get_object_or_404(User, pk=pk)

    # Prevent editing own account here (use Profile instead)
    if target == request.user:
        messages.info(request, 'To edit your own account, use the Profile page.')
        return redirect('accounts:profile')

    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=target)
        if form.is_valid():
            form.save()
            AuditLog.objects.create(
                user=request.user,
                action='updated',
                ip_address=get_client_ip(request),
                details={'action_type': 'user_edited', 'target_user': target.username}
            )
            messages.success(request, f'User "{target.username}" updated.')
            return redirect('accounts:user_list')
    else:
        form = UserEditForm(instance=target)

    return render(request, 'accounts/management/edit.html', {'form': form, 'target': target})


@_admin_required
def user_reset_password(request, pk):
    target = get_object_or_404(User, pk=pk)

    if request.method == 'POST':
        form = ResetPasswordForm(request.POST)
        if form.is_valid():
            target.set_password(form.cleaned_data['new_password1'])
            target.save()
            AuditLog.objects.create(
                user=request.user,
                action='updated',
                ip_address=get_client_ip(request),
                details={'action_type': 'password_reset', 'target_user': target.username}
            )
            messages.success(request, f'Password for "{target.username}" has been reset.')
            return redirect('accounts:user_list')
    else:
        form = ResetPasswordForm()

    return render(request, 'accounts/management/reset_password.html', {'form': form, 'target': target})


@_admin_required
def user_toggle_active(request, pk):
    if request.method == 'POST':
        target = get_object_or_404(User, pk=pk)
        if target == request.user:
            messages.error(request, 'You cannot deactivate your own account.')
            return redirect('accounts:user_list')
        target.is_active = not target.is_active
        target.save()
        status = 'activated' if target.is_active else 'deactivated'
        AuditLog.objects.create(
            user=request.user,
            action='updated',
            ip_address=get_client_ip(request),
            details={'action_type': f'user_{status}', 'target_user': target.username}
        )
        messages.success(request, f'User "{target.username}" has been {status}.')
    return redirect('accounts:user_list')


@_admin_required
def user_force_password_change(request, pk):
    if request.method == 'POST':
        target = get_object_or_404(User, pk=pk)
        target.force_password_change = True
        target.save(update_fields=['force_password_change'])
        AuditLog.objects.create(
            user=request.user,
            action='updated',
            ip_address=get_client_ip(request),
            details={'action_type': 'force_password_change', 'target_user': target.username}
        )
        messages.warning(request,
            f'{target.username} will be required to change their password on next login.')
    return redirect('accounts:user_list')
