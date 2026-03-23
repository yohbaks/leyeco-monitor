from django.urls import path
from .views import CustomLoginView, CustomLogoutView
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/',          CustomLoginView.as_view(),  name='login'),
    path('logout/',         CustomLogoutView.as_view(), name='logout'),
    path('profile/',        views.profile,              name='profile'),
    path('password/',       views.change_password,      name='change_password'),
    # User management
    path('users/',                       views.user_list,           name='user_list'),
    path('users/new/',                   views.user_create,         name='user_create'),
    path('users/<int:pk>/edit/',         views.user_edit,           name='user_edit'),
    path('users/<int:pk>/reset-password/', views.user_reset_password, name='user_reset_password'),
    path('users/<int:pk>/toggle/',       views.user_toggle_active,      name='user_toggle_active'),
    path('users/<int:pk>/force-password/', views.user_force_password_change, name='user_force_password'),
]
