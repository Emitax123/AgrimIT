"""
Context processor liviano para los contadores del sidebar (REDESIGN §3.2/§7.3).

Expone `project_count`, `receivables_count` y `clients_count` en todas las páginas
para que las píldoras `.count` del sidebar (ya cableadas en base_template.html) sean
consistentes en toda la app, no solo en Inicio. Guardado contra usuarios anónimos.
"""
from django.db.models import F

from apps.accounting.models import Account
from apps.clients.models import Client
from apps.project_admin.models import Project


def sidebar_counters(request):
    user = getattr(request, 'user', None)
    if user is None or not user.is_authenticated:
        return {}

    project_count = Project.objects.filter(user=user, closed=False).count()

    receivables_count = (Account.objects
                         .filter(project__user=user, project__closed=False, estimated__gt=0)
                         .annotate(saldo=F('estimated') - F('advance'))
                         .filter(saldo__gt=0)
                         .count())

    clients_count = Client.objects.filter(user=user).count()

    return {
        'project_count': project_count,
        'receivables_count': receivables_count,
        'clients_count': clients_count,
    }
