from django.urls import path
from . import views

app_name = 'transactions'

urlpatterns = [
    path('', views.transaction_list, name='list'),
    path('new/', views.transaction_create, name='create'),
    path('<int:pk>/', views.transaction_detail, name='detail'),
    path('<int:pk>/receipt/', views.transaction_receipt, name='receipt'),
    path('<int:pk>/void-request/', views.void_request, name='void_request'),
    path('<int:pk>/void-approve/', views.void_approve,   name='void_approve'),
    path('biller/',                  views.biller_history, name='biller_history'),
]
