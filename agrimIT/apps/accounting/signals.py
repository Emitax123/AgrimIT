"""Señales de accounting (Plan 04, item 2).

Centralizan la lógica de negocio financiera que antes vivía en
``accounting.views.create_acc_entry``: cuando se registra un AccountMovement,
se actualizan los saldos de su Account y el resumen mensual del usuario.

El movimiento es la única fuente de verdad del evento; los agregados (saldos de
la cuenta y MonthlyFinancialSummary) se derivan de él.
"""
import logging

from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import AccountMovement, MonthlyFinancialSummary

logger = logging.getLogger(__name__)


@receiver(post_save, sender=AccountMovement, dispatch_uid="accounting.apply_account_movement")
def apply_account_movement(sender, instance, created, **kwargs):
    """Aplica el efecto de un AccountMovement recién creado a la cuenta y al
    resumen mensual. Solo actúa en la creación (los movimientos no se editan)."""
    if not created:
        return

    account = instance.account
    try:
        project_type = account.project.type
    except ObjectDoesNotExist:
        project_type = None

    account.apply_movement(instance)
    MonthlyFinancialSummary.record_movement(instance, project_type)
