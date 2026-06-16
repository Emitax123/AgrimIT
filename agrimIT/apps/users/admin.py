from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, StudioProfile


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin configuration for custom User model"""
    
    # Fields to display in the user list
    list_display = (
        'username', 
        'email', 
        'first_name', 
        'last_name', 
        'phone_number',
        'is_active', 
        'is_staff', 
        'date_joined'
    )
    
    # Add custom fields to the existing fieldsets
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': ('phone_number',)
        }),
    )
    
    # Add custom fields to the add user form
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Additional Info', {
            'fields': ('first_name', 'last_name', 'email', 'phone_number')
        }),
    )


@admin.register(StudioProfile)
class StudioProfileAdmin(admin.ModelAdmin):
    """Edición de los datos del estudio que aparecen en la factura (REDESIGN §7.7)."""
    list_display = ('user', 'studio_name', 'professional_name', 'license_number')
    search_fields = ('user__username', 'studio_name', 'professional_name')
    fieldsets = (
        ('Estudio', {'fields': ('user', 'studio_name', 'professional_name', 'license_number')}),
        ('Contacto', {'fields': ('address', 'phone', 'email')}),
        ('Pago', {'fields': ('cbu', 'alias', 'payment_terms')}),
    )