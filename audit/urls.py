from django.urls import path
from . import views

app_name = 'audit'

urlpatterns = [
    path('',        views.audit_list,    name='list'),
    path('export/', views.export_excel,  name='export_excel'),
]
