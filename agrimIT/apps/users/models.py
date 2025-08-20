from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.
class User(AbstractUser):
    first_name = models.CharField(max_length=30, blank=True, verbose_name='First Name')
    last_name = models.CharField(max_length=30, blank=True, verbose_name='Last Name')
    hone_number = models.CharField(max_length=15, blank=True, verbose_name='Teléfono')
    is_active = models.BooleanField(default=True, verbose_name='Is Active')
    is_staff = models.BooleanField(default=False, verbose_name='Is Staff')

    def __str__(self):
        return f"{self.get_full_name()} ({self.username})" if self.get_full_name() else self.username

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        ordering = ['username']