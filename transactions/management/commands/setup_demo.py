"""
Management command: python manage.py setup_demo

Creates:
  - admin user (admin / admin123)
  - manager user (manager / manager123)
  - 2 teller users (teller1, teller2 / teller123)
  - Sample transactions for today
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal


class Command(BaseCommand):
    help = 'Create demo users and sample data for testing'

    def handle(self, *args, **options):
        from accounts.models import User
        from transactions.models import Payment, CashDenomination
        from audit.models import AuditLog

        self.stdout.write('Setting up demo data...')

        # Create admin
        admin, _ = User.objects.get_or_create(username='admin', defaults={
            'role': 'admin', 'branch': 'Main Branch',
            'first_name': 'Admin', 'last_name': 'User',
            'is_staff': True, 'is_superuser': True,
        })
        admin.set_password('admin123')
        admin.save()
        self.stdout.write(self.style.SUCCESS('  ✓ Admin user: admin / admin123'))

        # Create manager
        manager, _ = User.objects.get_or_create(username='manager', defaults={
            'role': 'manager', 'branch': 'Main Branch',
            'first_name': 'Maria', 'last_name': 'Santos',
        })
        manager.set_password('manager123')
        manager.save()
        self.stdout.write(self.style.SUCCESS('  ✓ Manager user: manager / manager123'))

        # Create tellers
        teller1, _ = User.objects.get_or_create(username='teller1', defaults={
            'role': 'teller', 'branch': 'Main Branch',
            'first_name': 'Jose', 'last_name': 'Reyes',
        })
        teller1.set_password('teller123')
        teller1.save()

        teller2, _ = User.objects.get_or_create(username='teller2', defaults={
            'role': 'teller', 'branch': 'Main Branch',
            'first_name': 'Ana', 'last_name': 'Cruz',
        })
        teller2.set_password('teller123')
        teller2.save()
        self.stdout.write(self.style.SUCCESS('  ✓ Teller users: teller1, teller2 / teller123'))

        # Sample transactions
        samples = [
            {'biller_name': 'Juan dela Cruz', 'biller_account_number': '012345678', 'bill_amount': Decimal('1200.00'), 'cash_received': Decimal('1210.00'), 'teller': teller1},
            {'biller_name': 'Maria Villanueva', 'biller_account_number': '023456789', 'bill_amount': Decimal('850.00'), 'cash_received': Decimal('1000.00'), 'teller': teller1},
            {'biller_name': 'Roberto Bacalso', 'biller_account_number': '034567890', 'bill_amount': Decimal('3200.00'), 'cash_received': Decimal('3210.00'), 'teller': teller2},
            {'biller_name': 'Lorna Tangco', 'biller_account_number': '045678901', 'bill_amount': Decimal('560.00'), 'cash_received': Decimal('600.00'), 'teller': teller2},
        ]

        for s in samples:
            if not Payment.objects.filter(biller_name=s['biller_name']).exists():
                p = Payment(**s)
                p.save()
                CashDenomination.objects.create(payment=p, denomination=1000, quantity=1)
                AuditLog.objects.create(user=s['teller'], action='created', target_txn=p, details={'demo': True})

        self.stdout.write(self.style.SUCCESS('  ✓ Sample transactions created'))
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Demo setup complete! Run: python manage.py runserver'))
        self.stdout.write('  Dashboard: http://127.0.0.1:8000/')
        self.stdout.write('  Login with any of the credentials above.')
