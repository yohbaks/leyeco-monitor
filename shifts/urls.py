from django.urls import path
from . import views

app_name = 'shifts'

urlpatterns = [
    path('',              views.shift_list,   name='list'),
    path('open/',         views.open_shift,   name='open'),
    path('<int:pk>/close/', views.close_shift, name='close'),
    path('<int:pk>/',     views.shift_detail, name='detail'),
]
