"""Tests de roles de equipo (Plan 04, item 3).

Semántica de roles:
  - owner  -> control total del grupo.
  - member -> puede compartir sus propios proyectos con el grupo.
  - viewer -> solo lectura (ver grupo y proyectos compartidos).
  - no-miembro -> sin acceso.
"""
import pytest
from django.urls import reverse

from apps.teams.models import Team, ProjectShare

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# 1. Helpers de rol en el modelo Team
# ---------------------------------------------------------------------------

class TestTeamRoleHelpers:

    def test_owner_role(self, team_factory):
        team = team_factory()
        assert team.get_user_role(team.owner) == 'owner'
        assert team.user_can_view(team.owner) is True
        assert team.user_can_manage(team.owner) is True
        assert team.user_can_share(team.owner) is True

    def test_member_role(self, team_factory, membership_factory, user_factory):
        team = team_factory()
        member = user_factory()
        membership_factory(team=team, user=member, role='member')
        assert team.get_user_role(member) == 'member'
        assert team.user_can_view(member) is True
        assert team.user_can_manage(member) is False
        assert team.user_can_share(member) is True

    def test_viewer_role(self, team_factory, membership_factory, user_factory):
        team = team_factory()
        viewer = user_factory()
        membership_factory(team=team, user=viewer, role='viewer')
        assert team.get_user_role(viewer) == 'viewer'
        assert team.user_can_view(viewer) is True
        assert team.user_can_manage(viewer) is False
        assert team.user_can_share(viewer) is False

    def test_non_member_role(self, team_factory, user_factory):
        team = team_factory()
        stranger = user_factory()
        assert team.get_user_role(stranger) is None
        assert team.user_can_view(stranger) is False
        assert team.user_can_share(stranger) is False

    def test_inactive_membership_no_da_rol(self, team_factory, membership_factory, user_factory):
        team = team_factory()
        user = user_factory()
        membership_factory(team=team, user=user, role='member', is_active=False)
        assert team.get_user_role(user) is None


# ---------------------------------------------------------------------------
# 2. Team.shareable_by
# ---------------------------------------------------------------------------

class TestShareableBy:

    def test_incluye_grupos_propios(self, team_factory):
        team = team_factory()
        assert team in Team.shareable_by(team.owner)

    def test_incluye_grupos_donde_es_member(self, team_factory, membership_factory, user_factory):
        team = team_factory()
        member = user_factory()
        membership_factory(team=team, user=member, role='member')
        assert team in Team.shareable_by(member)

    def test_excluye_grupos_donde_es_viewer(self, team_factory, membership_factory, user_factory):
        team = team_factory()
        viewer = user_factory()
        membership_factory(team=team, user=viewer, role='viewer')
        assert team not in Team.shareable_by(viewer)

    def test_excluye_membership_inactivo(self, team_factory, membership_factory, user_factory):
        team = team_factory()
        user = user_factory()
        membership_factory(team=team, user=user, role='member', is_active=False)
        assert team not in Team.shareable_by(user)


# ---------------------------------------------------------------------------
# 3. Vistas: compartir proyectos según rol
# ---------------------------------------------------------------------------

class TestShareViewsByRole:

    def test_member_puede_compartir_proyecto_propio(
        self, client, team_factory, membership_factory, user_factory, project_factory
    ):
        team = team_factory()
        member = user_factory()
        membership_factory(team=team, user=member, role='member')
        project = project_factory(user=member)

        client.force_login(member)
        client.post(reverse('project_share', args=[project.pk]), {'team': team.pk, 'notes': ''})

        assert ProjectShare.objects.filter(project=project, team=team, is_active=True).exists()

    def test_viewer_no_puede_compartir(
        self, client, team_factory, membership_factory, user_factory, project_factory
    ):
        team = team_factory()
        viewer = user_factory()
        membership_factory(team=team, user=viewer, role='viewer')
        project = project_factory(user=viewer)

        client.force_login(viewer)
        client.post(reverse('project_share', args=[project.pk]), {'team': team.pk, 'notes': ''})

        assert not ProjectShare.objects.filter(project=project, team=team).exists()


# ---------------------------------------------------------------------------
# 4. Vistas: lectura y acciones de gestión según rol
# ---------------------------------------------------------------------------

class TestTeamDetailAccess:

    def test_no_miembro_no_ve_detalle(self, client, team_factory, user_factory):
        team = team_factory(name="GRUPO_SECRETO")
        stranger = user_factory()
        client.force_login(stranger)
        resp = client.get(reverse('team_detail', args=[team.pk]))
        assert resp.status_code == 302
        assert b"GRUPO_SECRETO" not in resp.content

    def test_viewer_ve_detalle(self, client, team_factory, membership_factory, user_factory):
        team = team_factory()
        viewer = user_factory()
        membership_factory(team=team, user=viewer, role='viewer')
        client.force_login(viewer)
        resp = client.get(reverse('team_detail', args=[team.pk]))
        assert resp.status_code == 200

    def test_viewer_ve_proyectos_compartidos(self, client, membership_factory, user_factory):
        viewer = user_factory()
        membership_factory(user=viewer, role='viewer')
        client.force_login(viewer)
        resp = client.get(reverse('shared_projects'))
        assert resp.status_code == 200


class TestOwnerOnlyActions:

    def test_member_no_puede_editar_grupo(
        self, client, team_factory, membership_factory, user_factory
    ):
        team = team_factory(name="ORIGINAL")
        member = user_factory()
        membership_factory(team=team, user=member, role='member')

        client.force_login(member)
        resp = client.post(
            reverse('team_edit', args=[team.pk]),
            {'name': 'HACKEADO', 'description': '', 'members_usernames': ''},
        )
        assert resp.status_code == 404
        team.refresh_from_db()
        assert team.name == "ORIGINAL"
