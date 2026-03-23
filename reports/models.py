from django.db import models
from django.conf import settings
from decimal import Decimal


class EODReconciliation(models.Model):
    """End-of-day reconciliation record locked by manager/admin."""
    STATUS_OPEN   = 'open'
    STATUS_CLOSED = 'closed'

    STATUS_CHOICES = [
        (STATUS_OPEN,   'Open'),
        (STATUS_CLOSED, 'Closed'),
    ]

    date            = models.DateField(unique=True)
    status          = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_OPEN)

    # Computed totals (snapshotted at close time)
    total_transactions  = models.PositiveIntegerField(default=0)
    total_bill_amount   = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    total_service_fees  = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'))
    total_collected     = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    total_change_given  = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    declared_cash       = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    discrepancy         = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))

    closed_by  = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='eod_closures')
    closed_at  = models.DateTimeField(null=True, blank=True)
    notes      = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"EOD {self.date} — {self.get_status_display()}"

    class Meta:
        ordering = ['-date']
        verbose_name = 'EOD Reconciliation'
        verbose_name_plural = 'EOD Reconciliations'
