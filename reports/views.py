import io
from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.utils import timezone

from .logic import (
    daily_summary, range_summary, teller_breakdown,
    voided_transactions, transaction_rows, build_excel, build_pdf_html
)
from .models import EODReconciliation
from transactions.models import Payment
from audit.models import AuditLog


def _manager_required(view_func):
    from functools import wraps
    @wraps(view_func)
    @login_required
    def wrapped(request, *args, **kwargs):
        if not request.user.is_admin_or_manager():
            messages.error(request, 'Reports are only accessible to managers and admins.')
            return redirect('dashboard:index')
        return view_func(request, *args, **kwargs)
    return wrapped


def _parse_dates(request):
    today = timezone.now().date()
    date_from_str = request.GET.get('date_from', today.strftime('%Y-%m-%d'))
    date_to_str   = request.GET.get('date_to',   today.strftime('%Y-%m-%d'))
    try:
        date_from = date.fromisoformat(date_from_str)
        date_to   = date.fromisoformat(date_to_str)
    except ValueError:
        date_from = date_to = today
    if date_from > date_to:
        date_from, date_to = date_to, date_from
    return date_from, date_to


# ── Main reports hub ─────────────────────────────────────────

@_manager_required
def index(request):
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)
    month_start = today.replace(day=1)

    ctx = {
        'today'      : today,
        'today_sum'  : daily_summary(today),
        'month_sum'  : range_summary(month_start, today),
        'recent_eod' : EODReconciliation.objects.order_by('-date')[:7],
    }
    return render(request, 'reports/index.html', ctx)


# ── Daily report ─────────────────────────────────────────────

@_manager_required
def daily_report(request):
    today = timezone.now().date()
    report_date_str = request.GET.get('date', today.strftime('%Y-%m-%d'))
    try:
        report_date = date.fromisoformat(report_date_str)
    except ValueError:
        report_date = today

    summary  = daily_summary(report_date)
    tellers  = teller_breakdown(report_date, report_date)
    payments = transaction_rows(report_date, report_date)
    voids    = voided_transactions(report_date, report_date)

    ctx = {
        'report_date': report_date,
        'summary'    : summary,
        'tellers'    : tellers,
        'payments'   : payments,
        'voids'      : voids,
        'today'      : today,
    }
    return render(request, 'reports/daily.html', ctx)


# ── Range report ─────────────────────────────────────────────

@_manager_required
def range_report(request):
    today = timezone.now().date()
    date_from, date_to = _parse_dates(request)

    summary  = range_summary(date_from, date_to)
    tellers  = teller_breakdown(date_from, date_to)
    voids    = voided_transactions(date_from, date_to)

    # Chart data (JSON-safe)
    chart_labels = [str(d['day']) for d in summary['daily']]
    chart_collected = [float(d['collected'] or 0) for d in summary['daily']]
    chart_fees      = [float(d['fees']      or 0) for d in summary['daily']]

    ctx = {
        'date_from'      : date_from,
        'date_to'        : date_to,
        'summary'        : summary,
        'tellers'        : tellers,
        'voids'          : voids,
        'chart_labels'   : chart_labels,
        'chart_collected': chart_collected,
        'chart_fees'     : chart_fees,
        'today'          : today,
    }
    return render(request, 'reports/range.html', ctx)


# ── EOD Reconciliation ───────────────────────────────────────

@_manager_required
def eod_reconciliation(request):
    today = timezone.now().date()
    summary = daily_summary(today)
    eod, _ = EODReconciliation.objects.get_or_create(date=today)

    if request.method == 'POST' and eod.status == EODReconciliation.STATUS_OPEN:
        declared = request.POST.get('declared_cash', '0')
        notes    = request.POST.get('notes', '')
        try:
            declared = float(declared)
        except ValueError:
            declared = 0.0

        from decimal import Decimal
        eod.total_transactions = summary['txn_count']
        eod.total_bill_amount  = summary['total_bill']
        eod.total_service_fees = summary['total_fees']
        eod.total_collected    = summary['total_collected']
        eod.total_change_given = summary['total_change']
        eod.declared_cash      = Decimal(str(declared))
        eod.discrepancy        = eod.declared_cash - eod.total_collected
        eod.status             = EODReconciliation.STATUS_CLOSED
        eod.closed_by          = request.user
        eod.notes              = notes
        eod.closed_at          = timezone.now()
        eod.save()

        AuditLog.objects.create(
            user=request.user,
            action='updated',
            ip_address=request.META.get('REMOTE_ADDR'),
            details={
                'action_type': 'eod_closed',
                'date': str(today),
                'declared': declared,
                'discrepancy': float(eod.discrepancy),
            }
        )

        if eod.discrepancy == 0:
            messages.success(request, f'EOD for {today} closed. Perfectly balanced!')
        elif eod.discrepancy > 0:
            messages.success(request, f'EOD closed. Overage: ₱{eod.discrepancy:,.2f}')
        else:
            messages.warning(request, f'EOD closed. Shortage: ₱{abs(eod.discrepancy):,.2f} — please investigate.')

        # Send email notifications
        try:
            from settings_app.notifications import send_eod_shortage, send_daily_summary
            from reports.logic import teller_breakdown as tb
            teller_data = tb(today, today)
            send_eod_shortage(eod, request.user)
            send_daily_summary(eod, teller_data, request.user)
        except Exception:
            pass

        return redirect('reports:eod')

    tellers  = teller_breakdown(today, today)
    payments = transaction_rows(today, today)

    ctx = {
        'today'   : today,
        'summary' : summary,
        'eod'     : eod,
        'tellers' : tellers,
        'payments': payments,
    }
    return render(request, 'reports/eod.html', ctx)


# ── Excel export ─────────────────────────────────────────────

@_manager_required
def export_excel(request):
    date_from, date_to = _parse_dates(request)
    teller_id = request.GET.get('teller_id') or None

    wb = build_excel(date_from, date_to, teller_id)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    filename = f"leyeco_report_{date_from}_{date_to}.xlsx"
    response = HttpResponse(
        buf.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# ── PDF export ───────────────────────────────────────────────

@_manager_required
def export_pdf(request):
    date_from, date_to = _parse_dates(request)

    html = build_pdf_html(date_from, date_to)

    try:
        import weasyprint
        pdf = weasyprint.HTML(string=html).write_pdf()
        filename = f"leyeco_report_{date_from}_{date_to}.pdf"
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except Exception as e:
        # Fallback: return the HTML if WeasyPrint fails (e.g. missing system fonts)
        return HttpResponse(html, content_type='text/html')


# ── Chart data API ───────────────────────────────────────────

@_manager_required
def chart_data(request):
    date_from, date_to = _parse_dates(request)
    summary = range_summary(date_from, date_to)
    return JsonResponse({
        'labels'    : [str(d['day']) for d in summary['daily']],
        'collected' : [float(d['collected'] or 0) for d in summary['daily']],
        'fees'      : [float(d['fees'] or 0) for d in summary['daily']],
        'counts'    : [d['count'] for d in summary['daily']],
    })


# ── Advanced Reports ─────────────────────────────────────────

@_manager_required
def advanced_reports(request):
    from django.db.models.functions import TruncMonth, ExtractHour
    from django.db.models import Sum, Count, Avg
    from transactions.models import Payment
    from django.utils import timezone
    import json

    # Monthly income — last 12 months
    from datetime import date
    today = timezone.now().date()
    twelve_months_ago = today.replace(day=1)
    from dateutil.relativedelta import relativedelta
    twelve_months_ago = today - relativedelta(months=11)
    twelve_months_ago = twelve_months_ago.replace(day=1)

    monthly = (
        Payment.objects.filter(status='completed', created_at__date__gte=twelve_months_ago)
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(collected=Sum('total_due'), fees=Sum('service_fee'), count=Count('id'))
        .order_by('month')
    )
    monthly_labels  = [str(r['month'])[:7] for r in monthly]
    monthly_collect = [float(r['collected'] or 0) for r in monthly]
    monthly_fees    = [float(r['fees'] or 0) for r in monthly]
    monthly_counts  = [r['count'] for r in monthly]

    # Peak hours — all time
    hourly = (
        Payment.objects.filter(status='completed')
        .annotate(hour=ExtractHour('created_at'))
        .values('hour')
        .annotate(count=Count('id'), collected=Sum('total_due'))
        .order_by('hour')
    )
    hour_map = {r['hour']: r for r in hourly}
    peak_labels    = [f'{h:02d}:00' for h in range(24)]
    peak_counts    = [hour_map.get(h, {}).get('count', 0) for h in range(24)]
    peak_collected = [float(hour_map.get(h, {}).get('collected') or 0) for h in range(24)]

    # Top 10 billers
    top_billers = (
        Payment.objects.filter(status='completed')
        .values('biller_account_number', 'biller_name')
        .annotate(count=Count('id'), total=Sum('bill_amount'))
        .order_by('-count')[:10]
    )

    # Teller comparison
    from django.contrib.auth import get_user_model
    User = get_user_model()
    teller_compare = (
        Payment.objects.filter(status='completed')
        .values('teller__id', 'teller__first_name', 'teller__last_name', 'teller__username')
        .annotate(count=Count('id'), collected=Sum('total_due'), fees=Sum('service_fee'))
        .order_by('-collected')
    )
    tc_names     = []
    tc_collected = []
    tc_fees      = []
    for t in teller_compare:
        fn = t['teller__first_name']
        ln = t['teller__last_name']
        tc_names.append((f'{fn} {ln}'.strip() or t['teller__username'])[:15])
        tc_collected.append(float(t['collected'] or 0))
        tc_fees.append(float(t['fees'] or 0))

    # EOD shortage history
    from reports.models import EODReconciliation
    shortage_history = EODReconciliation.objects.filter(
        status='closed', discrepancy__lt=0
    ).order_by('-date')[:20]

    ctx = {
        'monthly_labels'  : json.dumps(monthly_labels),
        'monthly_collect' : json.dumps(monthly_collect),
        'monthly_fees'    : json.dumps(monthly_fees),
        'monthly_counts'  : json.dumps(monthly_counts),
        'peak_labels'     : json.dumps(peak_labels),
        'peak_counts'     : json.dumps(peak_counts),
        'peak_collected'  : json.dumps(peak_collected),
        'top_billers'     : top_billers,
        'tc_names'        : json.dumps(tc_names),
        'tc_collected'    : json.dumps(tc_collected),
        'tc_fees'         : json.dumps(tc_fees),
        'shortage_history': shortage_history,
        'today'           : today,
    }
    return render(request, 'reports/advanced.html', ctx)
