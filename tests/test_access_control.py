"""Tests de control de acceso (Plan 04, item 1).

Verifican dos garantias de seguridad:
1. Las vistas con @login_required redirigen al login si no hay sesion.
2. Un usuario no puede LEER ni MODIFICAR objetos de otro usuario.

La asercion clave en los tests cross-user es el *resultado de seguridad*
(el objeto de la victima no se filtra ni se muta), no el codigo de estado
exacto: las vistas responden de formas distintas (302 redirect, 404, o render
con error) pero todas deben proteger el dato.
"""
import pytest
from django.urls import reverse

from apps.accounting.models import AccountMovement
from apps.clients.models import Client
from apps.project_admin.models import Project, ProjectFiles, ProjectNote

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# 1. login_required
# ---------------------------------------------------------------------------

class TestLoginRequired:
    """Sin sesion, las vistas protegidas redirigen al login (302)."""

    @pytest.mark.parametrize("urlname", [
        "index",
        "projects",
        "create",
        "clients",
        "history",
        "import_projects",
    ])
    def test_redirige_a_login_sin_sesion(self, client, urlname):
        resp = client.get(reverse(urlname))
        assert resp.status_code == 302
        assert "login" in resp.url


# ---------------------------------------------------------------------------
# 2. Proyectos: un usuario no ve ni edita proyectos ajenos
# ---------------------------------------------------------------------------

class TestProjectAccessControl:

    def test_no_puede_ver_proyecto_ajeno(self, as_owner, other, project_factory):
        victim = project_factory(user=other, titular_name="SECRETO_VICTIMA")
        resp = as_owner.get(reverse("projectview", args=[victim.pk]))
        # Redirige (no muestra el proyecto) y no filtra el dato.
        assert resp.status_code == 302
        assert b"SECRETO_VICTIMA" not in resp.content

    def test_no_puede_eliminar_proyecto_ajeno(self, as_owner, other, project_factory):
        victim = project_factory(user=other)
        as_owner.post(reverse("delete", args=[victim.pk]))
        assert Project.objects.filter(pk=victim.pk).exists()

    def test_no_puede_cerrar_proyecto_ajeno(self, as_owner, other, project_factory):
        victim = project_factory(user=other, closed=False)
        as_owner.post(reverse("close", args=[victim.pk]))
        victim.refresh_from_db()
        assert victim.closed is False

    def test_no_puede_duplicar_proyecto_ajeno(self, as_owner, owner, other, project_factory):
        victim = project_factory(user=other)
        as_owner.post(reverse("duplicate", args=[victim.pk]))
        # No se crea ninguna copia para el atacante.
        assert Project.objects.filter(user=owner).count() == 0
        assert Project.objects.count() == 1

    def test_no_puede_modificar_proyecto_ajeno(self, as_owner, other, project_factory):
        victim = project_factory(user=other, titular_name="ORIGINAL")
        as_owner.post(reverse("modification", args=[victim.pk]), {"titular": "HACKEADO"})
        victim.refresh_from_db()
        assert victim.titular_name == "ORIGINAL"

    def test_no_puede_full_mod_proyecto_ajeno(self, as_owner, other, project_factory):
        victim = project_factory(user=other, titular_name="ORIGINAL")
        resp = as_owner.post(reverse("fullmodification", args=[victim.pk]), {"type": "Mensura"})
        # full_mod_view endurecido: redirige en vez de lanzar 500.
        assert resp.status_code == 302
        victim.refresh_from_db()
        assert victim.titular_name == "ORIGINAL"

    def test_no_puede_ver_archivos_de_proyecto_ajeno(self, as_owner, other, project_factory):
        victim = project_factory(user=other)
        resp = as_owner.get(reverse("files", args=[victim.pk]))
        assert resp.status_code == 302

    def test_no_puede_descargar_archivo_de_proyecto_ajeno(self, as_owner, other, project_factory):
        victim = project_factory(user=other)
        resp = as_owner.get(reverse("download", args=[victim.pk]))
        assert resp.status_code == 404

    def test_no_puede_subir_archivo_a_proyecto_ajeno(self, as_owner, other, project_factory):
        victim = project_factory(user=other)
        resp = as_owner.post(reverse("upload", args=[victim.pk]))
        assert resp.status_code == 404
        assert ProjectFiles.objects.filter(project=victim).count() == 0

    def test_no_puede_borrar_archivo_de_proyecto_ajeno(self, as_owner, other, project_factory):
        victim = project_factory(user=other)
        f = ProjectFiles.objects.create(project=victim, name="x.pdf", url="http://x/x.pdf")
        # delete_file redirige al referer; lo proveemos para evitar redirect(None).
        as_owner.post(reverse("deletefile", args=[victim.pk]), HTTP_REFERER="/projects/")
        assert ProjectFiles.objects.filter(pk=f.pk).exists()


# ---------------------------------------------------------------------------
# 3. Notas de proyecto
# ---------------------------------------------------------------------------

class TestProjectNotesAccessControl:

    def test_no_puede_agregar_nota_a_proyecto_ajeno(self, as_owner, other, project_factory):
        victim = project_factory(user=other)
        resp = as_owner.post(
            reverse("add_project_note", args=[victim.pk]),
            data='{"title": "t", "description": "d"}',
            content_type="application/json",
        )
        assert resp.status_code == 404
        assert ProjectNote.objects.filter(project=victim).count() == 0

    def test_no_puede_borrar_nota_de_proyecto_ajeno(self, as_owner, other, project_factory):
        victim = project_factory(user=other)
        note = ProjectNote.objects.create(
            project=victim, user=other, title="t", description="d"
        )
        resp = as_owner.post(reverse("delete_project_note", args=[victim.pk, note.id]))
        assert resp.status_code == 404
        assert ProjectNote.objects.filter(pk=note.pk).exists()


# ---------------------------------------------------------------------------
# 4. Clientes
# ---------------------------------------------------------------------------

class TestClientAccessControl:

    def test_no_puede_leer_json_de_cliente_ajeno(self, as_owner, other, client_factory):
        victim = client_factory(user=other, name="Cliente Secreto")
        resp = as_owner.get(reverse("client_json", args=[victim.pk]))
        assert resp.status_code == 404
        assert b"Cliente Secreto" not in resp.content

    def test_no_puede_ocultar_cliente_ajeno(self, as_owner, other, client_factory):
        victim = client_factory(user=other)
        resp = as_owner.get(reverse("clientedislist", args=[victim.pk]))
        assert resp.status_code == 404
        assert Client.objects.filter(pk=victim.pk).exists()

    def test_no_puede_eliminar_cliente_ajeno(self, as_owner, other, client_factory):
        victim = client_factory(user=other)
        as_owner.get(reverse("deleteclient", args=[victim.pk]))
        assert Client.objects.filter(pk=victim.pk).exists()

    def test_no_puede_crear_proyecto_para_cliente_ajeno(self, as_owner, owner, other, client_factory):
        victim = client_factory(user=other)
        as_owner.post(reverse("clientprojectcreate", args=[victim.pk]), {"type": "Mensura"})
        assert Project.objects.filter(user=owner).count() == 0


# ---------------------------------------------------------------------------
# 5. Contabilidad
# ---------------------------------------------------------------------------

class TestAccountingAccessControl:

    def test_no_puede_abrir_form_de_movimiento_de_proyecto_ajeno(self, as_owner, other, project_factory):
        victim = project_factory(user=other)
        resp = as_owner.get(reverse("accform", args=[victim.pk]))
        assert resp.status_code == 404

    def test_no_puede_crear_movimiento_en_proyecto_ajeno(self, as_owner, other, project_factory):
        victim = project_factory(user=other)
        resp = as_owner.post(
            reverse("accform", args=[victim.pk]),
            {"movement_type": "ADV", "amount": "100"},
        )
        assert resp.status_code == 404
        assert AccountMovement.objects.count() == 0
