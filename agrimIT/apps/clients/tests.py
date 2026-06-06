from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from .models import Client

User = get_user_model()


class ClientCreateAjaxTests(TestCase):
    """Alta rapida de cliente via modal del form de proyecto (tarea 4.4)."""

    def setUp(self):
        self.user = User.objects.create_user(username='agrim', password='secret123')
        self.url = reverse('client_create_ajax')

    def test_requiere_login(self):
        response = self.client.post(self.url, {'name': 'Juan'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Client.objects.count(), 0)

    def test_crea_cliente_scoped_al_usuario(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {'name': 'Juan Perez', 'phone': '123'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        client = Client.objects.get(pk=data['id'])
        self.assertEqual(client.user, self.user)
        self.assertEqual(client.name, 'Juan Perez')
        self.assertEqual(client.phone, '123')
        self.assertTrue(client.flag)
        self.assertEqual(data['name'], 'Juan Perez')

    def test_nombre_vacio_devuelve_400(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {'name': '   ', 'phone': '123'})
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())
        self.assertEqual(Client.objects.count(), 0)

    def test_get_no_permitido(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)
