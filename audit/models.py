from django.db import models
from django.conf import settings


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('created',       'Transaction Created'),
        ('updated',       'Transaction Updated'),
        ('void_requested','Void Requested'),
        ('void_approved', 'Void Approved'),
        ('void_rejected', 'Void Rejected'),
        ('login',         'User Login'),
        ('logout',        'User Logout'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='audit_logs'
    )
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    target_txn = models.ForeignKey(
        'transactions.Payment',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='audit_logs'
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    details = models.JSONField(default=dict)

    def __str__(self):
        return f"{self.get_action_display()} by {self.user} at {self.timestamp:%Y-%m-%d %H:%M}"

    class Meta:
        ordering = ['-timestamp']
        # No 'change' or 'delete' — audit logs are immutable
        default_permissions = ('add', 'view')
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'

    def delete(self, *args, **kwargs):
        raise PermissionError('Audit logs cannot be deleted.')
