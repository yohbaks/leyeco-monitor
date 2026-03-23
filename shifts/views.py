from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Count

from .models import Shift
from audit.models import AuditLog


def get_ip(request):
    x = request.META.get('HTTP_X_FORWARDED_FOR')
    return x.split(',')[0] if x else request.META.get('REMOTE_ADDR')


@login_required
def shift_list(request):
    if request.user.is_teller():
        shifts = Shift.objects.filter(teller=request.user).order_by('-opened_at')[:30]
    else:
        shifts = Shift.objects.select_related('teller').order_by('-opened_at')[:100]

    # Check if teller has open shift today
    today = timezone.now().date()
    open_shift = None
    if request.user.is_teller():
        open_shift = Shift.objects.filter(
            teller=request.user, date=today, status=Shift.STATUS_OPEN
        ).first()

    return render(request, 'shifts/list.html', {
        'shifts': shifts,
        'open_shift': open_shift,
        'today': today,
    })


@login_required
def open_shift(request):
    today = timezone.now().date()

    # Check if already has open shift today
    existing = Shift.objects.filter(
        teller=request.user, date=today, status=Shift.STATUS_OPEN
    ).first()
    if existing:
        messages.warning(request, 'You already have an open shift for today.')
        return redirect('shifts:list')

    if request.method == 'POST':
        try:
            opening_cash = Decimal(request.POST.get('opening_cash', '0'))
        except Exception:
            opening_cash = Decimal('0')

        shift = Shift.objects.create(
            teller=request.user,
            date=today,
            opening_cash=opening_cash,
            status=Shift.STATUS_OPEN,
        )
        AuditLog.objects.create(
            user=request.user,
            action='updated',
            ip_address=get_ip(request),
            details={
                'action_type': 'shift_opened',
                'shift_id': shift.pk,
                'opening_cash': str(opening_cash),
            }
        )
        messages.success(request, f'Shift opened with ₱{opening_cash:,.2f} starting cash.')
        return redirect('shifts:list')

    return render(request, 'shifts/open.html', {'today': today})


@login_required
def close_shift(request, pk):
    shift = get_object_or_404(Shift, pk=pk, status=Shift.STATUS_OPEN)

    # Only the shift owner or admin/manager can close
    if shift.teller != request.user and not request.user.is_admin_or_manager():
        messages.error(request, 'You can only close your own shift.')
        return redirect('shifts:list')

    # Get this teller's transactions for the shift date
    from transactions.models import Payment
    from django.db.models import Sum, Count
    txns = Payment.objects.filter(
        teller=shift.teller,
        created_at__date=shift.date,
        status='completed'
    )
    agg = txns.aggregate(
        total_collected=Sum('total_due'),
        total_fees=Sum('service_fee'),
        count=Count('id'),
    )
    total_collected = agg['total_collected'] or Decimal('0')
    total_fees      = agg['total_fees']      or Decimal('0')
    count           = agg['count']           or 0
    expected_cash   = shift.opening_cash + total_collected

    if request.method == 'POST':
        try:
            closing_cash = Decimal(request.POST.get('closing_cash', '0'))
        except Exception:
            closing_cash = Decimal('0')

        notes = request.POST.get('notes', '')
        discrepancy = closing_cash - expected_cash

        shift.closing_cash       = closing_cash
        shift.closed_at          = timezone.now()
        shift.status             = Shift.STATUS_CLOSED
        shift.total_transactions = count
        shift.total_collected    = total_collected
        shift.total_fees         = total_fees
        shift.expected_cash      = expected_cash
        shift.discrepancy        = discrepancy
        shift.notes              = notes
        shift.save()

        AuditLog.objects.create(
            user=request.user,
            action='updated',
            ip_address=get_ip(request),
            details={
                'action_type': 'shift_closed',
                'shift_id': shift.pk,
                'discrepancy': str(discrepancy),
            }
        )

        if discrepancy == 0:
            messages.success(request, 'Shift closed. Cash is perfectly balanced!')
        elif discrepancy < 0:
            messages.warning(request,
                f'Shift closed. Shortage of ₱{abs(discrepancy):,.2f} detected.')
        else:
            messages.success(request,
                f'Shift closed. Overage of ₱{discrepancy:,.2f}.')

        return redirect('shifts:detail', pk=shift.pk)

    return render(request, 'shifts/close.html', {
        'shift'          : shift,
        'txns'           : txns.order_by('-created_at'),
        'total_collected': total_collected,
        'total_fees'     : total_fees,
        'count'          : count,
        'expected_cash'  : expected_cash,
    })


@login_required
def shift_detail(request, pk):
    shift = get_object_or_404(Shift, pk=pk)
    if shift.teller != request.user and not request.user.is_admin_or_manager():
        messages.error(request, 'Access denied.')
        return redirect('shifts:list')

    txns = shift.get_transactions().order_by('-created_at')
    return render(request, 'shifts/detail.html', {'shift': shift, 'txns': txns})
