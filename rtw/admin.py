from django.contrib import admin
from .models import Category, Product, Sale, SaleItem


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name',)


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    readonly_fields = ('subtotal',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'sku', 'size', 'color', 'selling_price', 'stock_quantity', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('name', 'sku', 'color')
    list_editable = ('stock_quantity', 'is_active')


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('sale_number', 'customer_name', 'served_by', 'total_amount', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('sale_number', 'customer_name')
    readonly_fields = ('sale_number', 'subtotal', 'total_amount', 'change_given', 'created_at', 'updated_at')
    inlines = [SaleItemInline]
