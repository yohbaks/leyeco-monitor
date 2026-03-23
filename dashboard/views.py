from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone
from django.db.models import Sum, Count
from decimal import Decimal
import json

from transactions.models import Payment


@login_required
def index(request):
    today = timezone.now().date()
    base_qs = Payment.objects.filter(created_at__date=today)

    if request.user.is_teller():
        base_qs = base_qs.filter(teller=request.user)

    completed = base_qs.filter(status='completed')
    pending_voids = Payment.objects.filter(status='pending_void')

    stats = completed.aggregate(
        total_collected=Sum('total_due'),
        total_bill=Sum('bill_amount'),
        total_fees=Sum('service_fee'),
        txn_count=Count('id'),
    )

    teller_summary = []
    if request.user.is_admin_or_manager():
        from django.contrib.auth import get_user_model
        User = get_user_model()
        tellers = User.objects.filter(role='teller', is_active=True)
        for teller in tellers:
            t_stats = completed.filter(teller=teller).aggregate(
                total=Sum('total_due'),
                count=Count('id'),
                fees=Sum('service_fee'),
            )
            teller_summary.append({
                'teller': teller,
                'total': t_stats['total'] or Decimal('0'),
                'count': t_stats['count'] or 0,
                'fees':  t_stats['fees']  or Decimal('0'),
            })

    recent = base_qs.select_related('teller').order_by('-created_at')[:10]

    # 30-day chart data
    from datetime import timedelta
    from django.db.models.functions import TruncDate
    thirty_days_ago = today - timedelta(days=29)
    chart_data = (
        Payment.objects.filter(
            status='completed',
            created_at__date__gte=thirty_days_ago,
        )
        .annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(collected=Sum('total_due'), fees=Sum('service_fee'), count=Count('id'))
        .order_by('day')
    )
    # Fill all 30 days (including zeros)
    day_map = {str(row['day']): row for row in chart_data}
    chart_labels, chart_collected, chart_fees, chart_counts = [], [], [], []
    for i in range(30):
        d = str(thirty_days_ago + timedelta(days=i))
        row = day_map.get(d, {})
        chart_labels.append(d)
        chart_collected.append(float(row.get('collected') or 0))
        chart_fees.append(float(row.get('fees') or 0))
        chart_counts.append(row.get('count') or 0)

    # Open shift status (for teller)
    open_shift = None
    if request.user.is_teller():
        try:
            from shifts.models import Shift
            open_shift = Shift.objects.filter(
                teller=request.user, date=today, status='open'
            ).first()
        except Exception:
            pass

    context = {
        'today'           : today,
        'total_collected' : stats['total_collected'] or Decimal('0'),
        'total_fees'      : stats['total_fees']      or Decimal('0'),
        'total_bill'      : stats['total_bill']      or Decimal('0'),
        'txn_count'       : stats['txn_count']       or 0,
        'pending_void_count': pending_voids.count(),
        'teller_summary'  : teller_summary,
        'recent_payments' : recent,
        'open_shift'      : open_shift,
        'chart_labels'    : json.dumps(chart_labels),
        'chart_collected' : json.dumps(chart_collected),
        'chart_fees'      : json.dumps(chart_fees),
        'chart_counts'    : json.dumps(chart_counts),
    }
    return render(request, 'dashboard/index.html', context)
