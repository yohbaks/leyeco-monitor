from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/',        admin.site.urls),
    path('accounts/',     include('accounts.urls',     namespace='accounts')),
    path('transactions/', include('transactions.urls', namespace='transactions')),
    path('reports/',      include('reports.urls',      namespace='reports')),
    path('audit/',        include('audit.urls',        namespace='audit')),
    path('shifts/',       include('shifts.urls',       namespace='shifts')),
    path('settings/',     include('settings_app.urls', namespace='settings_app')),
    path('backup/',       include('backup.urls',       namespace='backup')),
    path('rtw/',          include('rtw.urls',           namespace='rtw')),
    path('gcash/',        include('gcash.urls',         namespace='gcash')),
    path('',              include('dashboard.urls',    namespace='dashboard')),
]
