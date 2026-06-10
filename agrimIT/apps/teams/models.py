from django.db import models
from django.db.models import Q
from apps.users.models import User
from apps.project_admin.models import Project


class Team(models.Model):
    """
    Grupo de trabajo para colaboración entre usuarios
    """
    name = models.CharField(max_length=200, verbose_name='Nombre del Grupo')
    description = models.TextField(blank=True, verbose_name='Descripción')
    owner = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='owned_teams',
        verbose_name='Propietario'
    )
    created = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Creación')
    updated = models.DateTimeField(auto_now=True, verbose_name='Última Actualización')
    is_active = models.BooleanField(default=True, verbose_name='Activo')
    
    class Meta:
        verbose_name = 'Equipo de Trabajo'
        verbose_name_plural = 'Equipos de Trabajo'
        ordering = ['-created']
        indexes = [
            models.Index(fields=['owner', '-created']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} (Propietario: {self.owner.username})"
    
    def get_members_count(self):
        """Retorna el número total de miembros incluido el propietario"""
        return self.memberships.filter(is_active=True).count() + 1

    def get_shared_projects_count(self):
        """Retorna el número de proyectos compartidos con este grupo"""
        return self.shared_projects.filter(is_active=True).count()

    # --- Roles y permisos (Plan 04, item 3) -------------------------------
    # Jerarquía: owner > member > viewer.
    #   owner  -> control total del grupo (editar/eliminar, gestionar miembros).
    #   member -> colaborador: puede compartir sus propios proyectos con el grupo.
    #   viewer -> solo lectura: ver el grupo y los proyectos compartidos.

    def get_user_role(self, user):
        """Rol efectivo de `user` en este grupo: 'owner'/'member'/'viewer' o None."""
        if not user or not user.is_authenticated:
            return None
        if self.owner_id == user.id:
            return 'owner'
        membership = self.memberships.filter(user=user, is_active=True).first()
        return membership.role if membership else None

    def user_can_view(self, user):
        """True si `user` puede ver el grupo (owner, member o viewer)."""
        return self.get_user_role(user) is not None

    def user_can_manage(self, user):
        """True si `user` puede gestionar el grupo (solo el owner)."""
        return self.get_user_role(user) == 'owner'

    def user_can_share(self, user):
        """True si `user` puede compartir proyectos con el grupo (owner o member)."""
        return self.get_user_role(user) in ('owner', 'member')

    @classmethod
    def shareable_by(cls, user):
        """Grupos activos donde `user` puede compartir: propios o donde es member."""
        if not user or not user.is_authenticated:
            return cls.objects.none()
        return cls.objects.filter(
            Q(owner=user) |
            Q(memberships__user=user, memberships__role='member', memberships__is_active=True),
            is_active=True,
        ).distinct()


class TeamMembership(models.Model):
    """
    Relación entre usuarios y equipos
    """
    ROLE_CHOICES = (
        ('member', 'Miembro'),
        ('viewer', 'Visualizador'),
    )
    
    team = models.ForeignKey(
        Team, 
        on_delete=models.CASCADE, 
        related_name='memberships',
        verbose_name='Equipo'
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='team_memberships',
        verbose_name='Usuario'
    )
    role = models.CharField(
        max_length=20, 
        choices=ROLE_CHOICES, 
        default='viewer',
        verbose_name='Rol'
    )
    joined_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Ingreso')
    is_active = models.BooleanField(default=True, verbose_name='Activo')
    
    class Meta:
        verbose_name = 'Miembro de Equipo'
        verbose_name_plural = 'Miembros de Equipo'
        unique_together = ['team', 'user']
        ordering = ['-joined_at']
        indexes = [
            models.Index(fields=['team', 'is_active']),
            models.Index(fields=['user', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.user.username} en {self.team.name} ({self.get_role_display()})"


class ProjectShare(models.Model):
    """
    Proyectos compartidos con equipos
    """
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='team_shares',
        verbose_name='Proyecto'
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name='shared_projects',
        verbose_name='Equipo'
    )
    shared_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='projects_shared',
        verbose_name='Compartido por'
    )
    shared_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Compartición')
    is_active = models.BooleanField(default=True, verbose_name='Activo')
    notes = models.TextField(blank=True, verbose_name='Notas')
    
    class Meta:
        verbose_name = 'Proyecto Compartido'
        verbose_name_plural = 'Proyectos Compartidos'
        unique_together = ['project', 'team']
        ordering = ['-shared_at']
        indexes = [
            models.Index(fields=['team', 'is_active']),
            models.Index(fields=['project', 'is_active']),
            models.Index(fields=['shared_by', '-shared_at']),
        ]
    
    def __str__(self):
        return f"{self.project} compartido con {self.team.name}"
