from decimal import Decimal, ROUND_HALF_UP
from django.db import models
from django.conf import settings
from django.utils import timezone


def generate_gcash_txn_number():
    today = timezone.now().strftime('%Y%m%d')
    count = GCashTransaction.objects.filter(created_at__date=timezone.now().date()).count() + 1
    return f"GCX-{today}-{count:05d}"


class GCashSettings(models.Model):
    fee_per_1000 = models.DecimalField(
        max_digits=8, decimal_places=2, default=Decimal('20.00'),
        verbose_name='Fee per \u20b11,000'
    )
    apply_rounding = models.BooleanField(default=True, verbose_name='Apply Rounding')
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='gcash_settings_updates'
    )

    class Meta:
        verbose_name = 'GCash Settings'

    def __str__(self):
        return f"GCash Settings (\u20b1{self.fee_per_1000}/1000)"

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def compute_fee(self, amount):
        amount = Decimal(str(amount))
        fee = (amount / Decimal('1000')) * self.fee_per_1000
        if self.apply_rounding:
            fee = fee.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        else:
            fee = fee.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return fee


class GCashTransaction(models.Model):
    TYPE_CASH_IN  = 'cash_in'
    TYPE_CASH_OUT = 'cash_out'
    TYPE_CHOICES  = [
        (TYPE_CASH_IN,  'Cash-In'),
        (TYPE_CASH_OUT, 'Cash-Out'),
    ]

    STATUS_COMPLETED = 'completed'
    STATUS_VOIDED    = 'voided'
    STATUS_CHOICES   = [
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_VOIDED,    'Voided'),
    ]

    txn_number   = models.CharField(max_length=30, unique=True, editable=False)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='gcash_transactions'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_COMPLETED)

    txn_type         = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name='Type')
    amount           = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Amount (\u20b1)')
    service_fee      = models.DecimalField(max_digits=8,  decimal_places=2, verbose_name='Service Fee (\u20b1)')
    customer_name    = models.CharField(max_length=200, blank=True, verbose_name='Customer Name')
    reference_number = models.CharField(max_length=100, blank=True, verbose_name='GCash Reference No.')
    notes            = models.TextField(blank=True)

    void_reason = models.TextField(blank=True)
    voided_by   = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='gcash_voids'
    )
    voided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.txn_number} \u2014 {self.get_txn_type_display()} \u20b1{self.amount}"

    def save(self, *args, **kwargs):
        if not self.txn_number:
            self.txn_number = generate_gcash_txn_number()
        super().save(*args, **kwargs)
