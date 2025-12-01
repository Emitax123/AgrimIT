from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Count
from django.http import JsonResponse, HttpResponse
from apps.project_admin.models import Project
from .models import Team, TeamMembership, ProjectShare
from .forms import TeamForm, AddMemberForm, ShareProjectForm
import logging

logger = logging.getLogger(__name__)


@login_required
def team_list(request):
    """Lista de todos los equipos del usuario (propios y donde es miembro)"""
    # Equipos donde el usuario es propietario
    owned_teams = Team.objects.filter(
        owner=request.user,
        is_active=True
    ).annotate(
        members_count=Count('memberships', filter=Q(memberships__is_active=True))
    ).order_by('-created')
    
    # Equipos donde el usuario es miembro
    member_teams = Team.objects.filter(
        memberships__user=request.user,
        memberships__is_active=True,
        is_active=True
    ).select_related('owner').annotate(
        members_count=Count('memberships', filter=Q(memberships__is_active=True))
    ).order_by('-created')
    
    context = {
        'owned_teams': owned_teams,
        'member_teams': member_teams,
    }
    
    return render(request, 'teams/team_list.html', context)


@login_required
@transaction.atomic
def team_create(request):
    """Crear un nuevo equipo"""
    if request.method == 'POST':
        form = TeamForm(request.POST, user=request.user)
        
        if form.is_valid():
            team = form.save(commit=False)
            team.owner = request.user
            team.save()
            
            # Agregar miembros
            members = form.cleaned_data.get('members_usernames', [])
            for user in members:
                TeamMembership.objects.create(
                    team=team,
                    user=user,
                    role='viewer'
                )
            
            messages.success(
                request, 
                f'Grupo "{team.name}" creado exitosamente con {len(members)} miembro(s).'
            )
            logger.info(f"Team created: {team.name} by {request.user.username}")
            
            return redirect('team_detail', pk=team.pk)
    else:
        form = TeamForm(user=request.user)
    
    return render(request, 'teams/team_form.html', {'form': form, 'action': 'Crear'})


@login_required
def team_detail(request, pk):
    """Ver detalles de un equipo"""
    team = get_object_or_404(Team, pk=pk, is_active=True)
    
    # Verificar que el usuario tenga acceso (propietario o miembro)
    is_owner = team.owner == request.user
    is_member = TeamMembership.objects.filter(
        team=team,
        user=request.user,
        is_active=True
    ).exists()
    
    if not (is_owner or is_member):
        messages.error(request, 'No tienes permiso para ver este grupo.')
        return redirect('team_list')
    
    # Obtener miembros
    members = TeamMembership.objects.filter(
        team=team,
        is_active=True
    ).select_related('user').order_by('-joined_at')
    
    # Obtener proyectos compartidos
    shared_projects = ProjectShare.objects.filter(
        team=team,
        is_active=True
    ).select_related('project', 'project__client', 'shared_by').order_by('-shared_at')
    
    # Formulario para agregar miembros (solo para el propietario)
    add_member_form = None
    if is_owner:
        add_member_form = AddMemberForm(team=team)
    
    context = {
        'team': team,
        'is_owner': is_owner,
        'is_member': is_member,
        'members': members,
        'shared_projects': shared_projects,
        'add_member_form': add_member_form,
    }
    
    return render(request, 'teams/team_detail.html', context)


@login_required
@transaction.atomic
def team_edit(request, pk):
    """Editar un equipo (solo propietario)"""
    team = get_object_or_404(Team, pk=pk, owner=request.user, is_active=True)
    
    if request.method == 'POST':
        form = TeamForm(request.POST, instance=team, user=request.user)
        
        if form.is_valid():
            team = form.save()
            
            # Actualizar miembros
            new_members = form.cleaned_data.get('members_usernames', [])
            current_members = list(TeamMembership.objects.filter(
                team=team,
                is_active=True
            ).select_related('user'))
            
            current_users = {m.user for m in current_members}
            new_users = set(new_members)
            
            # Eliminar miembros que ya no están
            for membership in current_members:
                if membership.user not in new_users:
                    membership.is_active = False
                    membership.save()
            
            # Agregar nuevos miembros
            for user in new_users:
                if user not in current_users:
                    TeamMembership.objects.create(
                        team=team,
                        user=user,
                        role='viewer'
                    )
            
            messages.success(request, f'Grupo "{team.name}" actualizado exitosamente.')
            logger.info(f"Team updated: {team.name} by {request.user.username}")
            
            return redirect('team_detail', pk=team.pk)
    else:
        form = TeamForm(instance=team, user=request.user)
    
    return render(request, 'teams/team_form.html', {
        'form': form,
        'action': 'Editar',
        'team': team
    })


@login_required
@transaction.atomic
def team_add_member(request, pk):
    """Agregar un miembro a un equipo (solo propietario)"""
    team = get_object_or_404(Team, pk=pk, owner=request.user, is_active=True)
    
    if request.method == 'POST':
        form = AddMemberForm(request.POST, team=team)
        
        if form.is_valid():
            user = form.cleaned_data['username']
            role = form.cleaned_data['role']
            
            TeamMembership.objects.create(
                team=team,
                user=user,
                role=role
            )
            
            messages.success(
                request,
                f'Usuario "{user.username}" agregado al grupo "{team.name}".'
            )
            logger.info(f"Member added to team {team.name}: {user.username}")
        else:
            for error in form.errors.values():
                messages.error(request, error[0])
    
    return redirect('team_detail', pk=team.pk)


@login_required
@transaction.atomic
def team_remove_member(request, pk, member_pk):
    """Remover un miembro de un equipo (solo propietario)"""
    team = get_object_or_404(Team, pk=pk, owner=request.user, is_active=True)
    membership = get_object_or_404(
        TeamMembership,
        pk=member_pk,
        team=team,
        is_active=True
    )
    
    if request.method == 'POST':
        username = membership.user.username
        membership.is_active = False
        membership.save()
        
        messages.success(
            request,
            f'Usuario "{username}" removido del grupo "{team.name}".'
        )
        logger.info(f"Member removed from team {team.name}: {username}")
    
    return redirect('team_detail', pk=team.pk)


@login_required
@transaction.atomic
def team_delete(request, pk):
    """Eliminar un equipo (solo propietario)"""
    team = get_object_or_404(Team, pk=pk, owner=request.user, is_active=True)
    
    if request.method == 'POST':
        team_name = team.name
        team.is_active = False
        team.save()
        
        messages.success(request, f'Grupo "{team_name}" eliminado exitosamente.')
        logger.info(f"Team deleted: {team_name} by {request.user.username}")
        
        return redirect('team_list')
    
    return render(request, 'teams/team_confirm_delete.html', {'team': team})


@login_required
@transaction.atomic
def project_share(request, project_pk):
    """Compartir un proyecto con un equipo"""
    project = get_object_or_404(Project, pk=project_pk, user=request.user)
    
    if request.method == 'POST':
        form = ShareProjectForm(request.POST, user=request.user, project=project)
        
        if form.is_valid():
            share = form.save(commit=False)
            share.project = project
            share.shared_by = request.user
            share.save()
            
            messages.success(
                request,
                f'Proyecto compartido con el grupo "{share.team.name}".'
            )
            logger.info(
                f"Project {project.pk} shared with team {share.team.name} by {request.user.username}"
            )
            
            return redirect('projectview', pk=project.pk)
    else:
        form = ShareProjectForm(user=request.user, project=project)
    
    return render(request, 'teams/project_share_form.html', {
        'form': form,
        'project': project
    })


@login_required
@transaction.atomic
def project_unshare(request, project_pk, share_pk):
    """Dejar de compartir un proyecto con un equipo"""
    project = get_object_or_404(Project, pk=project_pk, user=request.user)
    share = get_object_or_404(
        ProjectShare,
        pk=share_pk,
        project=project,
        is_active=True
    )
    
    if request.method == 'POST':
        team_name = share.team.name
        share.is_active = False
        share.save()
        
        messages.success(
            request,
            f'Proyecto dejó de compartirse con el grupo "{team_name}".'
        )
        logger.info(
            f"Project {project.pk} unshared from team {team_name} by {request.user.username}"
        )
    
    return redirect('projectview', pk=project.pk)


@login_required
def shared_projects(request):
    """Ver todos los proyectos compartidos conmigo a través de equipos"""
    # Obtener equipos donde el usuario es miembro
    user_teams = Team.objects.filter(
        memberships__user=request.user,
        memberships__is_active=True,
        is_active=True
    )
    
    # Obtener proyectos compartidos con esos equipos
    projects = ProjectShare.objects.filter(
        team__in=user_teams,
        is_active=True
    ).select_related(
        'project',
        'project__client',
        'project__user',
        'team',
        'shared_by'
    ).order_by('-shared_at')
    
    context = {
        'shared_projects': projects,
    }
    
    return render(request, 'teams/shared_projects.html', context)
