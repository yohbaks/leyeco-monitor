import json
from decimal import Decimal, InvalidOperation
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction as db_transaction
from django.db.models import Sum, Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import CategoryForm, ProductForm, SaleHeaderForm, VoidSaleForm, StockAdjustForm
from .models import Category, Product, Sale, SaleItem


# ─── Dashboard ────────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    today = timezone.localdate()
    sales_today = Sale.objects.filter(
        created_at__date=today, status=Sale.STATUS_COMPLETED
    )
    today_count = sales_today.count()
    today_revenue = sales_today.aggregate(t=Sum('total_amount'))['t'] or Decimal('0.00')
    today_profit = sum(
        (item.subtotal - item.product.cost_price * item.quantity)
        for sale in sales_today
        for item in sale.items.select_related('product')
    )

    recent_sales = Sale.objects.select_related('served_by').prefetch_related('items')[:10]
    low_stock = Product.objects.filter(is_active=True, stock_quantity__lte=5).order_by('stock_quantity')[:10]
    total_products = Product.objects.filter(is_active=True).count()
    out_of_stock = Product.objects.filter(is_active=True, stock_quantity=0).count()

    # 30-day trend data for chart
    from django.db.models.functions import TruncDate
    trend = (
        Sale.objects
        .filter(
            status=Sale.STATUS_COMPLETED,
            created_at__date__gte=today - timezone.timedelta(days=29),
        )
        .annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(revenue=Sum('total_amount'), count=Count('id'))
        .order_by('day')
    )
    trend_data = [
        {'date': str(r['day']), 'revenue': float(r['revenue']), 'count': r['count']}
        for r in trend
    ]

    return render(request, 'rtw/dashboard.html', {
        'today_count': today_count,
        'today_revenue': today_revenue,
        'today_profit': today_profit,
        'recent_sales': recent_sales,
        'low_stock': low_stock,
        'total_products': total_products,
        'out_of_stock': out_of_stock,
        'trend_data': json.dumps(trend_data),
    })


# ─── Categories ───────────────────────────────────────────────────────────────

@login_required
def category_list(request):
    if not request.user.is_admin_or_manager():
        messages.error(request, 'Access denied.')
        return redirect('rtw:dashboard')
    categories = Category.objects.annotate(product_count=Count('products'))
    return render(request, 'rtw/category_list.html', {'categories': categories})


@login_required
def category_save(request, pk=None):
    if not request.user.is_admin_or_manager():
        messages.error(request, 'Access denied.')
        return redirect('rtw:dashboard')
    instance = get_object_or_404(Category, pk=pk) if pk else None
    form = CategoryForm(request.POST or None, instance=instance)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Category saved.')
        return redirect('rtw:category_list')
    return render(request, 'rtw/category_form.html', {'form': form, 'instance': instance})


# ─── Products ─────────────────────────────────────────────────────────────────

@login_required
def product_list(request):
    qs = Product.objects.select_related('category')
    q = request.GET.get('q', '').strip()
    category = request.GET.get('category', '')
    status = request.GET.get('status', '')

    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(sku__icontains=q) | Q(color__icontains=q))
    if category:
        qs = qs.filter(category_id=category)
    if status == 'active':
        qs = qs.filter(is_active=True)
    elif status == 'inactive':
        qs = qs.filter(is_active=False)
    elif status == 'low':
        qs = qs.filter(is_active=True, stock_quantity__lte=5)
    elif status == 'out':
        qs = qs.filter(is_active=True, stock_quantity=0)

    paginator = Paginator(qs, 50)
    page = paginator.get_page(request.GET.get('page'))
    categories = Category.objects.filter(is_active=True)
    return render(request, 'rtw/product_list.html', {
        'page': page, 'categories': categories,
        'q': q, 'sel_category': category, 'sel_status': status,
    })


@login_required
def product_create(request):
    if not request.user.is_admin_or_manager():
        messages.error(request, 'Access denied.')
        return redirect('rtw:product_list')
    form = ProductForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Product added.')
        return redirect('rtw:product_list')
    return render(request, 'rtw/product_form.html', {'form': form, 'title': 'Add Product'})


@login_required
def product_edit(request, pk):
    if not request.user.is_admin_or_manager():
        messages.error(request, 'Access denied.')
        return redirect('rtw:product_list')
    product = get_object_or_404(Product, pk=pk)
    form = ProductForm(request.POST or None, instance=product)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Product updated.')
        return redirect('rtw:product_list')
    return render(request, 'rtw/product_form.html', {'form': form, 'title': 'Edit Product', 'product': product})


@login_required
def product_toggle(request, pk):
    if not request.user.is_admin_or_manager():
        messages.error(request, 'Access denied.')
        return redirect('rtw:product_list')
    product = get_object_or_404(Product, pk=pk)
    product.is_active = not product.is_active
    product.save(update_fields=['is_active'])
    state = 'activated' if product.is_active else 'deactivated'
    messages.success(request, f'"{product.name}" {state}.')
    return redirect('rtw:product_list')


@login_required
def product_stock_adjust(request, pk):
    if not request.user.is_admin_or_manager():
        messages.error(request, 'Access denied.')
        return redirect('rtw:product_list')
    product = get_object_or_404(Product, pk=pk)
    form = StockAdjustForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        adj = form.cleaned_data['adjustment']
        product.stock_quantity = max(0, product.stock_quantity + adj)
        product.save(update_fields=['stock_quantity'])
        messages.success(request, f'Stock for "{product}" updated to {product.stock_quantity}.')
        return redirect('rtw:product_list')
    return render(request, 'rtw/product_stock.html', {'form': form, 'product': product})


# ─── Sales ────────────────────────────────────────────────────────────────────

@login_required
def sale_list(request):
    qs = Sale.objects.select_related('served_by').prefetch_related('items')
    q = request.GET.get('q', '').strip()
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    status = request.GET.get('status', '')

    if q:
        qs = qs.filter(
            Q(sale_number__icontains=q) | Q(customer_name__icontains=q)
        )
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)
    if status:
        qs = qs.filter(status=status)

    # If teller, only show own sales
    if request.user.is_teller():
        qs = qs.filter(served_by=request.user)

    paginator = Paginator(qs, 50)
    page = paginator.get_page(request.GET.get('page'))

    total_sales = qs.filter(status=Sale.STATUS_COMPLETED).count()
    total_revenue = qs.filter(status=Sale.STATUS_COMPLETED).aggregate(t=Sum('total_amount'))['t'] or Decimal('0.00')

    return render(request, 'rtw/sale_list.html', {
        'page': page,
        'q': q, 'date_from': date_from, 'date_to': date_to, 'sel_status': status,
        'total_sales': total_sales, 'total_revenue': total_revenue,
    })


@login_required
def sale_create(request):
    products = Product.objects.filter(is_active=True, stock_quantity__gt=0).select_related('category').order_by('name')
    form = SaleHeaderForm(request.POST or None)

    if request.method == 'POST':
        items_json = request.POST.get('items_json', '[]')
        try:
            items_data = json.loads(items_json)
        except (json.JSONDecodeError, ValueError):
            items_data = []

        if not items_data:
            messages.error(request, 'Please add at least one item to the sale.')
            return render(request, 'rtw/sale_create.html', {'form': form, 'products': products})

        if form.is_valid():
            with db_transaction.atomic():
                sale = form.save(commit=False)
                sale.served_by = request.user
                sale.subtotal = Decimal('0.00')
                sale.total_amount = Decimal('0.00')
                sale.change_given = Decimal('0.00')
                sale.save()

                subtotal = Decimal('0.00')
                errors = []
                for row in items_data:
                    try:
                        product_id = int(row['product_id'])
                        qty = int(row['quantity'])
                        unit_price = Decimal(str(row['unit_price']))
                    except (KeyError, ValueError, InvalidOperation):
                        errors.append('Invalid item data submitted.')
                        continue

                    try:
                        product = Product.objects.select_for_update().get(pk=product_id, is_active=True)
                    except Product.DoesNotExist:
                        errors.append(f'Product ID {product_id} not found.')
                        continue

                    if product.stock_quantity < qty:
                        errors.append(
                            f'Insufficient stock for "{product.name}" '
                            f'(available: {product.stock_quantity}, requested: {qty}).'
                        )
                        continue

                    SaleItem.objects.create(
                        sale=sale,
                        product=product,
                        quantity=qty,
                        unit_price=unit_price,
                    )
                    product.stock_quantity -= qty
                    product.save(update_fields=['stock_quantity'])
                    subtotal += unit_price * qty

                if errors:
                    db_transaction.set_rollback(True)
                    for e in errors:
                        messages.error(request, e)
                    return render(request, 'rtw/sale_create.html', {'form': form, 'products': products})

                discount = sale.discount_amount or Decimal('0.00')
                sale.subtotal = subtotal
                sale.total_amount = max(subtotal - discount, Decimal('0.00'))
                sale.change_given = max(sale.cash_received - sale.total_amount, Decimal('0.00'))
                sale.save(update_fields=['subtotal', 'total_amount', 'change_given'])

            messages.success(request, f'Sale {sale.sale_number} recorded.')
            return redirect('rtw:sale_detail', pk=sale.pk)

    return render(request, 'rtw/sale_create.html', {'form': form, 'products': products})


@login_required
def sale_detail(request, pk):
    sale = get_object_or_404(
        Sale.objects.select_related('served_by', 'voided_by').prefetch_related('items__product'),
        pk=pk
    )
    return render(request, 'rtw/sale_detail.html', {'sale': sale})


@login_required
def sale_void(request, pk):
    sale = get_object_or_404(Sale, pk=pk)
    if sale.is_voided:
        messages.error(request, 'This sale is already voided.')
        return redirect('rtw:sale_detail', pk=pk)
    if not request.user.is_admin_or_manager():
        messages.error(request, 'Only managers or admins can void sales.')
        return redirect('rtw:sale_detail', pk=pk)

    form = VoidSaleForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        with db_transaction.atomic():
            # Restore stock
            for item in sale.items.select_related('product'):
                item.product.stock_quantity += item.quantity
                item.product.save(update_fields=['stock_quantity'])

            sale.status = Sale.STATUS_VOIDED
            sale.void_reason = form.cleaned_data['void_reason']
            sale.voided_by = request.user
            sale.voided_at = timezone.now()
            sale.save(update_fields=['status', 'void_reason', 'voided_by', 'voided_at'])

        messages.success(request, f'Sale {sale.sale_number} has been voided.')
        return redirect('rtw:sale_detail', pk=pk)

    return render(request, 'rtw/sale_void.html', {'sale': sale, 'form': form})


# ─── Reports ──────────────────────────────────────────────────────────────────

@login_required
def reports(request):
    if not request.user.is_admin_or_manager():
        messages.error(request, 'Access denied.')
        return redirect('rtw:dashboard')

    today = timezone.localdate()
    date_from_str = request.GET.get('date_from', str(today))
    date_to_str = request.GET.get('date_to', str(today))

    try:
        from datetime import date
        date_from = date.fromisoformat(date_from_str)
        date_to = date.fromisoformat(date_to_str)
    except ValueError:
        date_from = date_to = today

    completed = Sale.objects.filter(
        status=Sale.STATUS_COMPLETED,
        created_at__date__gte=date_from,
        created_at__date__lte=date_to,
    )

    agg = completed.aggregate(
        total_sales=Count('id'),
        total_revenue=Sum('total_amount'),
        total_discount=Sum('discount_amount'),
    )
    total_sales = agg['total_sales'] or 0
    total_revenue = agg['total_revenue'] or Decimal('0.00')
    total_discount = agg['total_discount'] or Decimal('0.00')

    # Gross profit
    items_in_range = SaleItem.objects.filter(
        sale__status=Sale.STATUS_COMPLETED,
        sale__created_at__date__gte=date_from,
        sale__created_at__date__lte=date_to,
    ).select_related('product')
    total_cost = sum(item.product.cost_price * item.quantity for item in items_in_range)
    gross_profit = total_revenue - Decimal(str(total_cost))

    # Top products by quantity sold
    top_products = (
        SaleItem.objects
        .filter(
            sale__status=Sale.STATUS_COMPLETED,
            sale__created_at__date__gte=date_from,
            sale__created_at__date__lte=date_to,
        )
        .values('product__name', 'product__category__name')
        .annotate(qty_sold=Sum('quantity'), revenue=Sum('subtotal'))
        .order_by('-qty_sold')[:10]
    )

    # Sales by category
    by_category = (
        SaleItem.objects
        .filter(
            sale__status=Sale.STATUS_COMPLETED,
            sale__created_at__date__gte=date_from,
            sale__created_at__date__lte=date_to,
        )
        .values('product__category__name')
        .annotate(qty_sold=Sum('quantity'), revenue=Sum('subtotal'))
        .order_by('-revenue')
    )

    # Daily trend
    from django.db.models.functions import TruncDate
    daily_trend = (
        completed
        .annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(revenue=Sum('total_amount'), count=Count('id'))
        .order_by('day')
    )
    trend_data = [
        {'date': str(r['day']), 'revenue': float(r['revenue']), 'count': r['count']}
        for r in daily_trend
    ]

    # Staff performance
    staff_perf = (
        completed
        .values('served_by__username', 'served_by__first_name', 'served_by__last_name')
        .annotate(sales_count=Count('id'), total=Sum('total_amount'))
        .order_by('-total')
    )

    return render(request, 'rtw/reports.html', {
        'date_from': date_from,
        'date_to': date_to,
        'total_sales': total_sales,
        'total_revenue': total_revenue,
        'total_discount': total_discount,
        'gross_profit': gross_profit,
        'top_products': top_products,
        'by_category': by_category,
        'staff_perf': staff_perf,
        'trend_data': json.dumps(trend_data),
    })


# ─── AJAX: product search for POS ─────────────────────────────────────────────

@login_required
def product_search_api(request):
    q = request.GET.get('q', '').strip()
    qs = Product.objects.filter(is_active=True, stock_quantity__gt=0)
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(sku__icontains=q))
    data = [
        {
            'id': p.pk,
            'name': str(p),
            'sku': p.sku,
            'price': str(p.selling_price),
            'stock': p.stock_quantity,
        }
        for p in qs[:20]
    ]
    return JsonResponse({'results': data})
