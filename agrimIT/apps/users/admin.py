from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin configuration for custom User model"""
    
    # Fields to display in the user list
    list_display = (
        'username', 
        'email', 
        'first_name', 
        'last_name', 
        'hone_number',
        'is_active', 
        'is_staff', 
        'date_joined'
    )
    
    # Add custom fields to the existing fieldsets
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': ('hone_number',)
        }),
    )
    
    # Add custom fields to the add user form
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Additional Info', {
            'fields': ('first_name', 'last_name', 'email', 'hone_number')
        }),
    )