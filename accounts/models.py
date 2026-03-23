from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_ADMIN = 'admin'
    ROLE_TELLER = 'teller'
    ROLE_MANAGER = 'manager'

    ROLE_CHOICES = [
        (ROLE_ADMIN, 'Admin'),
        (ROLE_TELLER, 'Teller'),
        (ROLE_MANAGER, 'Manager'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_TELLER)
    branch = models.CharField(max_length=100, blank=True, default='Main Branch')
    employee_id = models.CharField(max_length=30, blank=True)
    force_password_change = models.BooleanField(default=False, help_text='Force user to change password on next login')
    force_password_change = models.BooleanField(default=False,
        help_text='Force user to change password on next login.')

    def is_admin(self):
        return self.role == self.ROLE_ADMIN

    def is_teller(self):
        return self.role == self.ROLE_TELLER

    def is_manager(self):
        return self.role == self.ROLE_MANAGER

    def is_admin_or_manager(self):
        return self.role in (self.ROLE_ADMIN, self.ROLE_MANAGER)

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
