from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone


def generate_sale_number():
    today = timezone.now().strftime('%Y%m%d')
    count = Sale.objects.filter(created_at__date=timezone.now().date()).count() + 1
    return f"RTW-{today}-{count:05d}"


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'


class Product(models.Model):
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT,
        related_name='products', null=True, blank=True
    )
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=50, blank=True, verbose_name='SKU / Code')
    size = models.CharField(max_length=20, blank=True)
    color = models.CharField(max_length=50, blank=True)
    cost_price = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name='Cost Price (₱)', default=Decimal('0.00')
    )
    selling_price = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name='Selling Price (₱)'
    )
    stock_quantity = models.IntegerField(default=0, verbose_name='Stock Quantity')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        parts = [self.name]
        if self.size:
            parts.append(f"Size {self.size}")
        if self.color:
            parts.append(self.color)
        return ' · '.join(parts)

    @property
    def is_low_stock(self):
        return self.stock_quantity <= 5

    @property
    def profit_margin(self):
        if self.selling_price and self.cost_price:
            return self.selling_price - self.cost_price
        return Decimal('0.00')

    class Meta:
        ordering = ['name', 'size', 'color']
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        indexes = [
            models.Index(fields=['category']),
            models.Index(fields=['is_active']),
        ]


class Sale(models.Model):
    STATUS_COMPLETED = 'completed'
    STATUS_VOIDED = 'voided'

    STATUS_CHOICES = [
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_VOIDED, 'Voided'),
    ]

    sale_number = models.CharField(max_length=30, unique=True, editable=False)
    served_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='rtw_sales'
    )
    customer_name = models.CharField(max_length=200, blank=True, verbose_name='Customer Name (optional)')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_COMPLETED)

    # Financials
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2,
        default=Decimal('0.00'), verbose_name='Discount (₱)'
    )
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    cash_received = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name='Cash Received (₱)'
    )
    change_given = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    # Void fields
    void_reason = models.TextField(blank=True)
    voided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='rtw_voids'
    )
    voided_at = models.DateTimeField(null=True, blank=True)

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.sale_number:
            self.sale_number = generate_sale_number()
        super().save(*args, **kwargs)

    def recalculate_totals(self):
        """Recalculate subtotal, total, and change from sale items."""
        self.subtotal = sum(
            (item.subtotal for item in self.items.all()),
            Decimal('0.00')
        )
        self.total_amount = max(self.subtotal - self.discount_amount, Decimal('0.00'))
        self.change_given = max(self.cash_received - self.total_amount, Decimal('0.00'))
        Sale.objects.filter(pk=self.pk).update(
            subtotal=self.subtotal,
            total_amount=self.total_amount,
            change_given=self.change_given,
        )

    @property
    def is_voided(self):
        return self.status == self.STATUS_VOIDED

    def __str__(self):
        return f"{self.sale_number} — {self.customer_name or 'Walk-in'}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Sale'
        verbose_name_plural = 'Sales'
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['served_by', 'created_at']),
            models.Index(fields=['status']),
        ]


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='sale_items')
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, editable=False, default=Decimal('0.00'))

    def save(self, *args, **kwargs):
        self.subtotal = Decimal(str(self.unit_price)) * self.quantity
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quantity}× {self.product.name} @ ₱{self.unit_price}"

    class Meta:
        ordering = ['id']
        verbose_name = 'Sale Item'
        verbose_name_plural = 'Sale Items'
