from django.contrib import admin
from .models import GCashTransaction, GCashSettings

@admin.register(GCashSettings)
class GCashSettingsAdmin(admin.ModelAdmin):
    list_display = ['fee_per_1000', 'apply_rounding', 'updated_at', 'updated_by']

@admin.register(GCashTransaction)
class GCashTransactionAdmin(admin.ModelAdmin):
    list_display  = ['txn_number', 'txn_type', 'amount', 'service_fee', 'status', 'processed_by', 'created_at']
    list_filter   = ['txn_type', 'status', 'created_at']
    search_fields = ['txn_number', 'customer_name', 'reference_number']
    readonly_fields = ['txn_number', 'created_at', 'updated_at']
