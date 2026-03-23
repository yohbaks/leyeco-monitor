from django.db import models
from django.conf import settings
from decimal import Decimal


class Shift(models.Model):
    STATUS_OPEN   = 'open'
    STATUS_CLOSED = 'closed'
    STATUS_CHOICES = [
        (STATUS_OPEN,   'Open'),
        (STATUS_CLOSED, 'Closed'),
    ]

    teller          = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                        related_name='shifts')
    date            = models.DateField()
    status          = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_OPEN)

    # Opening
    opening_cash    = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'))
    opened_at       = models.DateTimeField(auto_now_add=True)

    # Closing
    closing_cash    = models.DecimalField(max_digits=10, decimal_places=2,
                                          null=True, blank=True)
    closed_at       = models.DateTimeField(null=True, blank=True)

    # Computed at close
    total_transactions = models.PositiveIntegerField(default=0)
    total_collected    = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    total_fees         = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'))
    expected_cash      = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    discrepancy        = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))

    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-opened_at']
        indexes = [
            models.Index(fields=['teller', 'date']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Shift — {self.teller.username} {self.date} ({self.get_status_display()})"

    @property
    def is_open(self):
        return self.status == self.STATUS_OPEN

    def get_transactions(self):
        from transactions.models import Payment
        return Payment.objects.filter(
            teller=self.teller,
            created_at__date=self.date,
            status='completed'
        )
