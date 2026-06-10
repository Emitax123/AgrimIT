"""Configuracion raiz de pytest: path del proyecto + factories compartidas.

`manage.py` vive en `agrimIT/`, asi que ese directorio debe estar en `sys.path`
para que `agrimIT.settings` y `apps.*` sean importables. Lo insertamos al
importar este conftest (lo mas temprano posible, antes de que pytest-django
configure Django).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "agrimIT"))

import factory
import pytest
from factory.django import DjangoModelFactory


# --- Factories (referencias a modelos por string para no depender del orden
#     de carga de apps de Django) ---------------------------------------------

class UserFactory(DjangoModelFactory):
    class Meta:
        model = "users.User"
        django_get_or_create = ("username",)
        skip_postgeneration_save = True  # el hook ya guarda explicitamente

    username = factory.Sequence(lambda n: f"user{n}")

    @factory.post_generation
    def password(obj, create, extracted, **kwargs):
        obj.set_password(extracted or "testpass123")
        if create:
            obj.save()


class ClientFactory(DjangoModelFactory):
    class Meta:
        model = "clients.Client"

    user = factory.SubFactory(UserFactory)
    name = factory.Sequence(lambda n: f"Cliente {n}")
    phone = "1122334455"
    email = factory.Sequence(lambda n: f"cliente{n}@example.com")
    id_type = "DNI"
    id_number = factory.Sequence(lambda n: str(30000000 + n))
    flag = True


class ProjectFactory(DjangoModelFactory):
    class Meta:
        model = "project_admin.Project"

    # El cliente comparte el dueño del proyecto (caso realista).
    user = factory.SubFactory(UserFactory)
    client = factory.SubFactory(ClientFactory, user=factory.SelfAttribute("..user"))
    type = "Mensura"
    titular_name = "Titular Test"
    titular_phone = "1100000000"


# --- Fixtures ----------------------------------------------------------------

@pytest.fixture
def owner(db):
    """Usuario autenticado en las pruebas (el 'atacante' en los tests de acceso)."""
    return UserFactory()


@pytest.fixture
def other(db):
    """Usuario victima: dueño de los objetos que `owner` no debe poder tocar."""
    return UserFactory()


@pytest.fixture
def as_owner(client, owner):
    """Cliente de test ya logueado como `owner`."""
    client.force_login(owner)
    return client


@pytest.fixture
def user_factory(db):
    return UserFactory


@pytest.fixture
def client_factory(db):
    return ClientFactory


@pytest.fixture
def project_factory(db):
    return ProjectFactory
