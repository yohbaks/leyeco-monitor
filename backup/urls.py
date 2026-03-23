from django.urls import path
from . import views

app_name = 'backup'

urlpatterns = [
    path('',       views.backup_index, name='index'),
    path('csv/',   views.export_csv,   name='export_csv'),
    path('full/',  views.full_backup,  name='full_backup'),
]
