from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone


def generate_txn_number():
    today = timezone.now().strftime('%Y%m%d')
    count = Payment.objects.filter(created_at__date=timezone.now().date()).count() + 1
    return f"LECO-{today}-{count:05d}"


class Payment(models.Model):
    STATUS_COMPLETED = 'completed'
    STATUS_VOIDED = 'voided'
    STATUS_PENDING_VOID = 'pending_void'

    STATUS_CHOICES = [
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_VOIDED, 'Voided'),
        (STATUS_PENDING_VOID, 'Pending Void Approval'),
    ]

    # Auto fields
    txn_number = models.CharField(max_length=30, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    teller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='payments'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_COMPLETED)

    # Customer / biller info
    biller_name = models.CharField(max_length=200)
    biller_account_number = models.CharField(max_length=50)
    leyeco_reference = models.CharField(max_length=100, blank=True, verbose_name='LEYECO Reference No.')

    # Financial fields
    bill_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Bill Amount (₱)')
    service_fee = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('10.00'))
    total_due = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    cash_received = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Cash Received (₱)')
    change_given = models.DecimalField(max_digits=10, decimal_places=2, editable=False)

    # Void management
    void_reason = models.TextField(blank=True)
    void_requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='void_requests'
    )
    void_approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='void_approvals'
    )
    void_at = models.DateTimeField(null=True, blank=True)

    notes = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        if not self.txn_number:
            self.txn_number = generate_txn_number()
        try:
            from settings_app.models import SystemSettings
            self.service_fee = SystemSettings.get().service_fee
        except Exception:
            self.service_fee = Decimal('10.00')
        self.total_due = self.bill_amount + self.service_fee
        self.change_given = max(self.cash_received - self.total_due, Decimal('0.00'))
        super().save(*args, **kwargs)

    @property
    def is_voided(self):
        return self.status == self.STATUS_VOIDED

    @property
    def is_pending_void(self):
        return self.status == self.STATUS_PENDING_VOID

    def __str__(self):
        return f"{self.txn_number} — {self.biller_name}"

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['teller', 'created_at']),
            models.Index(fields=['status']),
        ]


DENOMINATION_CHOICES = [
    (1000, '₱1,000'),
    (500,  '₱500'),
    (200,  '₱200'),
    (100,  '₱100'),
    (50,   '₱50'),
    (20,   '₱20'),
    (10,   '₱10'),
    (5,    '₱5'),
    (1,    '₱1'),
]


class CashDenomination(models.Model):
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='denominations')
    denomination = models.IntegerField(choices=DENOMINATION_CHOICES)
    quantity = models.PositiveIntegerField(default=0)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, editable=False)

    def save(self, *args, **kwargs):
        self.subtotal = Decimal(str(self.denomination * self.quantity))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"₱{self.denomination} × {self.quantity}"

    class Meta:
        ordering = ['-denomination']
