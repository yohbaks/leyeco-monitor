from django.db import models
from decimal import Decimal


class SystemSettings(models.Model):
    """
    Single-row settings table.
    Always use SystemSettings.get() to retrieve — never .all() or .filter().
    """
    # Business info
    business_name       = models.CharField(max_length=200, default='LEYECO Payment Center')
    branch_address      = models.CharField(max_length=300, blank=True, default='')
    receipt_footer      = models.CharField(max_length=200, blank=True,
                                           default='Thank you for using our payment service.')

    # Financials
    service_fee         = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('10.00'))

    # Email / SMTP
    email_enabled       = models.BooleanField(default=False)
    smtp_host           = models.CharField(max_length=200, default='smtp.gmail.com')
    smtp_port           = models.IntegerField(default=587)
    smtp_use_tls        = models.BooleanField(default=True)
    smtp_username       = models.CharField(max_length=200, blank=True)
    smtp_password       = models.CharField(max_length=200, blank=True)
    email_from          = models.CharField(max_length=200, blank=True,
                                           help_text='Display name + address e.g. LEYECO Monitor <you@gmail.com>')
    admin_email         = models.CharField(max_length=500, blank=True,
                                           help_text='Comma-separated list of admin emails to notify')

    # Notification toggles
    notify_void_request = models.BooleanField(default=True,
                                              verbose_name='Email on void request')
    notify_eod_shortage = models.BooleanField(default=True,
                                              verbose_name='Email on EOD shortage')
    notify_daily_summary= models.BooleanField(default=True,
                                              verbose_name='Send daily summary email at EOD')
    notify_new_user     = models.BooleanField(default=False,
                                              verbose_name='Welcome email to new users')

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'System Settings'

    def __str__(self):
        return f'System Settings — {self.business_name}'

    @classmethod
    def get(cls):
        """Always returns the single settings row, creating it if needed."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def get_admin_emails(self):
        """Returns list of admin email addresses."""
        if not self.admin_email:
            return []
        return [e.strip() for e in self.admin_email.split(',') if e.strip()]
