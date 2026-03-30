from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='GCashSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fee_per_1000', models.DecimalField(decimal_places=2, default='20.00', max_digits=8, verbose_name='Fee per \u20b11,000')),
                ('apply_rounding', models.BooleanField(default=True, verbose_name='Apply Rounding')),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='gcash_settings_updates', to=settings.AUTH_USER_MODEL)),
            ],
            options={'verbose_name': 'GCash Settings'},
        ),
        migrations.CreateModel(
            name='GCashTransaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('txn_number', models.CharField(editable=False, max_length=30, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('status', models.CharField(choices=[('completed', 'Completed'), ('voided', 'Voided')], default='completed', max_length=20)),
                ('txn_type', models.CharField(choices=[('cash_in', 'Cash-In'), ('cash_out', 'Cash-Out')], max_length=20, verbose_name='Type')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12, verbose_name='Amount (\u20b1)')),
                ('service_fee', models.DecimalField(decimal_places=2, max_digits=8, verbose_name='Service Fee (\u20b1)')),
                ('customer_name', models.CharField(blank=True, max_length=200, verbose_name='Customer Name')),
                ('reference_number', models.CharField(blank=True, max_length=100, verbose_name='GCash Reference No.')),
                ('notes', models.TextField(blank=True)),
                ('void_reason', models.TextField(blank=True)),
                ('voided_at', models.DateTimeField(blank=True, null=True)),
                ('processed_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='gcash_transactions', to=settings.AUTH_USER_MODEL)),
                ('voided_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='gcash_voids', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),
    ]
