from django.urls import path
from . import views

app_name = 'rtw'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # Categories
    path('categories/', views.category_list, name='category_list'),
    path('categories/add/', views.category_save, name='category_create'),
    path('categories/<int:pk>/edit/', views.category_save, name='category_edit'),

    # Products
    path('products/', views.product_list, name='product_list'),
    path('products/add/', views.product_create, name='product_create'),
    path('products/<int:pk>/edit/', views.product_edit, name='product_edit'),
    path('products/<int:pk>/toggle/', views.product_toggle, name='product_toggle'),
    path('products/<int:pk>/stock/', views.product_stock_adjust, name='product_stock'),

    # Sales
    path('sales/', views.sale_list, name='sale_list'),
    path('sales/new/', views.sale_create, name='sale_create'),
    path('sales/<int:pk>/', views.sale_detail, name='sale_detail'),
    path('sales/<int:pk>/void/', views.sale_void, name='sale_void'),

    # Reports
    path('reports/', views.reports, name='reports'),

    # AJAX
    path('api/products/', views.product_search_api, name='product_search_api'),
]
