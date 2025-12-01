from django.contrib import admin
from .models import Team, TeamMembership, ProjectShare


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'get_members_count', 'is_active', 'created']
    list_filter = ['is_active', 'created']
    search_fields = ['name', 'description', 'owner__username']
    readonly_fields = ['created', 'updated']
    
    fieldsets = (
        ('Información General', {
            'fields': ('name', 'description', 'owner', 'is_active')
        }),
        ('Fechas', {
            'fields': ('created', 'updated'),
            'classes': ('collapse',)
        }),
    )


@admin.register(TeamMembership)
class TeamMembershipAdmin(admin.ModelAdmin):
    list_display = ['user', 'team', 'role', 'is_active', 'joined_at']
    list_filter = ['role', 'is_active', 'joined_at']
    search_fields = ['user__username', 'team__name']
    readonly_fields = ['joined_at']


@admin.register(ProjectShare)
class ProjectShareAdmin(admin.ModelAdmin):
    list_display = ['project', 'team', 'shared_by', 'is_active', 'shared_at']
    list_filter = ['is_active', 'shared_at']
    search_fields = ['project__titular_name', 'team__name', 'shared_by__username']
    readonly_fields = ['shared_at']
