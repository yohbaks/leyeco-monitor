from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('',               views.index,             name='index'),
    path('daily/',         views.daily_report,       name='daily'),
    path('range/',         views.range_report,       name='range'),
    path('eod/',           views.eod_reconciliation, name='eod'),
    path('export/excel/',  views.export_excel,       name='export_excel'),
    path('export/pdf/',    views.export_pdf,         name='export_pdf'),
    path('api/chart/',     views.chart_data,         name='chart_data'),
    path('advanced/',      views.advanced_reports,   name='advanced'),
]
