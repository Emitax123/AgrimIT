from django.urls import path
from . import views

urlpatterns = [
    # Team management
    path('', views.team_list, name='team_list'),
    path('crear/', views.team_create, name='team_create'),
    path('<int:pk>/', views.team_detail, name='team_detail'),
    path('<int:pk>/editar/', views.team_edit, name='team_edit'),
    path('<int:pk>/eliminar/', views.team_delete, name='team_delete'),
    path('<int:pk>/agregar-miembro/', views.team_add_member, name='team_add_member'),
    path('<int:pk>/remover-miembro/<int:member_pk>/', views.team_remove_member, name='team_remove_member'),
    
    # Project sharing
    path('proyecto/<int:project_pk>/compartir/', views.project_share, name='project_share'),
    path('proyecto/<int:project_pk>/dejar-compartir/<int:share_pk>/', views.project_unshare, name='project_unshare'),
    path('proyectos-compartidos/', views.shared_projects, name='shared_projects'),
]
