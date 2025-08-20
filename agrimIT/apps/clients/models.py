from django.db import models
from apps.users.models import User

class Client(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='clients')
    name = models.CharField(max_length=100, verbose_name='Nombre')
    email = models.EmailField(null=True, blank=True, verbose_name='Email')
    ID_TYPE_CHOICES = (
        ('DNI', 'DNI'),
        ('CUIT', 'CUIT'),
        ('CUIL', 'CUIL'),
    )
    flag = models.BooleanField(default=True, verbose_name='Activo')
    id_type = models.CharField(max_length=8, choices=ID_TYPE_CHOICES, default='DNI', verbose_name='Tipo de Documento')
    id_number = models.CharField(max_length=13)
    phone = models.CharField(max_length=20, verbose_name='Telefono')
    def __str__(self):
        return f"{self.name} ({self.id_type}: {self.id_number})"