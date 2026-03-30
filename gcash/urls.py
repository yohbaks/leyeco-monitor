from django.urls import path
from . import views

app_name = 'gcash'

urlpatterns = [
    path('',                              views.dashboard,          name='dashboard'),
    path('new/',                          views.transaction_create, name='transaction_create'),
    path('transactions/',                 views.transaction_list,   name='transaction_list'),
    path('transactions/<int:pk>/',        views.transaction_detail, name='transaction_detail'),
    path('transactions/<int:pk>/edit/',   views.transaction_edit,   name='transaction_edit'),
    path('transactions/<int:pk>/void/',   views.transaction_void,   name='transaction_void'),
    path('reports/',                      views.reports,            name='reports'),
    path('settings/',                     views.gcash_settings,     name='settings'),
    path('api/fee/',                      views.fee_api,            name='fee_api'),
]
