from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.
class User(AbstractUser):
    first_name = models.CharField(max_length=30, blank=True, verbose_name='First Name')
    last_name = models.CharField(max_length=30, blank=True, verbose_name='Last Name')
    phone_number = models.CharField(max_length=15, blank=True, verbose_name='Teléfono')
    is_active = models.BooleanField(default=True, verbose_name='Is Active')
    is_staff = models.BooleanField(default=False, verbose_name='Is Staff')

    def __str__(self):
        return f"{self.get_full_name()} ({self.username})" if self.get_full_name() else self.username

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        ordering = ['username']


class StudioProfile(models.Model):
    """Datos del estudio para la factura no oficial (REDESIGN §7.7)."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='studio_profile')
    studio_name = models.CharField(max_length=120, default="Estudio de Agrimensura", verbose_name='Nombre del estudio')
    professional_name = models.CharField(max_length=120, blank=True, verbose_name='Profesional')
    license_number = models.CharField(max_length=40, blank=True, verbose_name='Matrícula')
    address = models.CharField(max_length=200, blank=True, verbose_name='Dirección')
    phone = models.CharField(max_length=40, blank=True, verbose_name='Teléfono')
    email = models.EmailField(blank=True, verbose_name='Email')
    cbu = models.CharField(max_length=40, blank=True, verbose_name='CBU')
    alias = models.CharField(max_length=40, blank=True, verbose_name='Alias')
    payment_terms = models.TextField(blank=True, verbose_name='Forma de pago')

    def __str__(self):
        return f"{self.studio_name} ({self.user.username})"

    class Meta:
        verbose_name = 'Perfil del estudio'
        verbose_name_plural = 'Perfiles del estudio'