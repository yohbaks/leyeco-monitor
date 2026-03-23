from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.db.models import Q, Sum, Count
from django.http import JsonResponse

from .models import Payment, CashDenomination
from .forms import PaymentForm, VoidRequestForm
from audit.models import AuditLog


def role_required(*roles):
    """Decorator to restrict views by user role."""
    from functools import wraps
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapped(request, *args, **kwargs):
            if request.user.role not in roles:
                messages.error(request, 'You do not have permission to access that page.')
                return redirect('dashboard:index')
            return view_func(request, *args, **kwargs)
        return wrapped
    return decorator


@login_required
def transaction_list(request):
    qs = Payment.objects.select_related('teller').all()

    # Tellers only see their own transactions
    if request.user.is_teller():
        qs = qs.filter(teller=request.user)

    # Search
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(
            Q(txn_number__icontains=q) |
            Q(biller_name__icontains=q) |
            Q(biller_account_number__icontains=q) |
            Q(leyeco_reference__icontains=q)
        )

    # Date filter
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)

    # Status filter
    status = request.GET.get('status', '')
    if status:
        qs = qs.filter(status=status)

    totals = qs.filter(status='completed').aggregate(
        total_collected=Sum('total_due'),
        total_bill=Sum('bill_amount'),
        total_fees=Sum('service_fee'),
        count=Count('id'),
    )

    # remove old cap
    context = {
        
        'totals': totals,
        'q': q,
        'date_from': date_from or '',
        'date_to': date_to or '',
        'status_filter': status,
    }
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(qs, 50)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    context["payments"] = page_obj
    context["page_obj"] = page_obj
    return render(request, "transactions/list.html", context)


@login_required
def transaction_create(request):
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.teller = request.user
            payment.save()

            # Save denominations
            denoms = form.get_denominations()
            for denom_value, qty in denoms.items():
                if qty > 0:
                    CashDenomination.objects.create(
                        payment=payment,
                        denomination=denom_value,
                        quantity=qty,
                    )

            # Audit log
            AuditLog.objects.create(
                user=request.user,
                action='created',
                target_txn=payment,
                ip_address=get_client_ip(request),
                details={
                    'txn_number': payment.txn_number,
                    'bill_amount': str(payment.bill_amount),
                    'total_due': str(payment.total_due),
                }
            )

            messages.success(
                request,
                f'Transaction {payment.txn_number} recorded successfully. '
                f'Change to give: ₱{payment.change_given:,.2f}'
            )
            return redirect('transactions:receipt', pk=payment.pk)
    else:
        form = PaymentForm()

    denom_fields = [
        (1000, '₱1,000'), (500, '₱500'), (200, '₱200'), (100, '₱100'),
        (50, '₱50'), (20, '₱20'), (10, '₱10'), (5, '₱5'), (1, '₱1'),
    ]
    # Duplicate detection — check if same account paid today
    duplicate_warning = None
    account_q = request.GET.get('account', '')
    if account_q:
        from django.utils import timezone
        today = timezone.now().date()
        dupes = Payment.objects.filter(
            biller_account_number=account_q,
            created_at__date=today,
            status='completed'
        ).select_related('teller')
        if dupes.exists():
            duplicate_warning = dupes

    return render(request, 'transactions/create.html', {
        'form': form,
        'denom_fields': denom_fields,
        'duplicate_warning': duplicate_warning,
        'prefill_account': account_q,
    })


@login_required
def transaction_detail(request, pk):
    payment = get_object_or_404(Payment, pk=pk)
    if request.user.is_teller() and payment.teller != request.user:
        messages.error(request, 'You can only view your own transactions.')
        return redirect('transactions:list')

    logs = AuditLog.objects.filter(target_txn=payment).order_by('timestamp')
    return render(request, 'transactions/detail.html', {'payment': payment, 'logs': logs})


@login_required
def transaction_receipt(request, pk):
    payment = get_object_or_404(Payment, pk=pk)
    return render(request, 'transactions/receipt.html', {'payment': payment})


@login_required
def void_request(request, pk):
    payment = get_object_or_404(Payment, pk=pk)

    if payment.status != Payment.STATUS_COMPLETED:
        messages.error(request, 'This transaction cannot be voided.')
        return redirect('transactions:detail', pk=pk)

    if request.user.is_teller() and payment.teller != request.user:
        messages.error(request, 'You can only request void for your own transactions.')
        return redirect('transactions:list')

    if request.method == 'POST':
        form = VoidRequestForm(request.POST)
        if form.is_valid():
            payment.status = Payment.STATUS_PENDING_VOID
            payment.void_reason = form.cleaned_data['void_reason']
            payment.void_requested_by = request.user
            payment.save()

            AuditLog.objects.create(
                user=request.user,
                action='void_requested',
                target_txn=payment,
                ip_address=get_client_ip(request),
                details={'reason': form.cleaned_data['void_reason']}
            )
            try:
                from settings_app.notifications import send_void_request
                send_void_request(payment, request.user)
            except Exception:
                pass
            messages.warning(request, f'Void request for {payment.txn_number} submitted. Awaiting admin approval.')
            return redirect('transactions:detail', pk=pk)
    else:
        form = VoidRequestForm()

    return render(request, 'transactions/void_request.html', {'payment': payment, 'form': form})


@role_required('admin', 'manager')
def void_approve(request, pk):
    payment = get_object_or_404(Payment, pk=pk, status=Payment.STATUS_PENDING_VOID)
    action = request.POST.get('action')

    if action == 'approve':
        payment.status = Payment.STATUS_VOIDED
        payment.void_approved_by = request.user
        payment.void_at = timezone.now()
        payment.save()
        AuditLog.objects.create(
            user=request.user,
            action='void_approved',
            target_txn=payment,
            ip_address=get_client_ip(request),
            details={}
        )
        messages.success(request, f'{payment.txn_number} has been voided.')
    elif action == 'reject':
        payment.status = Payment.STATUS_COMPLETED
        payment.void_reason = ''
        payment.void_requested_by = None
        payment.save()
        AuditLog.objects.create(
            user=request.user,
            action='void_rejected',
            target_txn=payment,
            ip_address=get_client_ip(request),
            details={}
        )
        messages.info(request, f'Void request for {payment.txn_number} was rejected.')

    return redirect('transactions:detail', pk=pk)


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')


@login_required
def biller_history(request):
    """Full payment history for a specific account number."""
    account = request.GET.get('account', '').strip()
    payments = None
    biller_name = None

    if account:
        from django.db.models import Sum, Count
        payments = Payment.objects.filter(
            biller_account_number=account
        ).select_related('teller').order_by('-created_at')
        if payments.exists():
            biller_name = payments.first().biller_name

    return render(request, 'transactions/biller_history.html', {
        'account'    : account,
        'payments'   : payments,
        'biller_name': biller_name,
    })
