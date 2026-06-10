"""Tests de logica financiera (Plan 04, item 1).

Cubren:
- Las propiedades `networth` / `net_worth` (fix B.1: advance - expense).
- `create_acc_entry`: actualiza la cuenta, crea el movimiento y agrega/actualiza
  el resumen mensual (`MonthlyFinancialSummary`) por tipo de proyecto.
"""
from decimal import Decimal

import pytest

from apps.accounting.models import Account, AccountMovement, MonthlyFinancialSummary
from apps.accounting.views import create_acc_entry

pytestmark = pytest.mark.django_db


# --- Propiedades de patrimonio ----------------------------------------------

def test_account_networth_es_advance_menos_expense(owner):
    acc = Account.objects.create(
        user=owner, advance=Decimal("1000.00"), expense=Decimal("300.00")
    )
    assert acc.networth == Decimal("700.00")


def test_account_networth_default_cero(owner):
    acc = Account.objects.create(user=owner)
    assert acc.networth == Decimal("0.00")


def test_summary_networth_es_advance_menos_expense(owner):
    s = MonthlyFinancialSummary.objects.create(
        user=owner, year=2026, month=6,
        total_advance=Decimal("900.00"), total_expenses=Decimal("200.00"),
    )
    assert s.net_worth == Decimal("700.00")


# --- create_acc_entry --------------------------------------------------------

def test_anticipo_actualiza_cuenta_movimiento_y_resumen(project_factory):
    project = project_factory(type="Mensura")

    create_acc_entry(project, "adv", new_value=Decimal("1000.00"))

    project.refresh_from_db()
    acc = project.account
    assert acc.advance == Decimal("1000.00")
    assert acc.networth == Decimal("1000.00")
    assert AccountMovement.objects.filter(account=acc, movement_type="ADV").count() == 1

    summary = MonthlyFinancialSummary.objects.get(user=project.user)
    assert summary.total_advance == Decimal("1000.00")
    assert summary.income_mensura == Decimal("1000.00")


def test_gasto_reduce_networth_y_actualiza_resumen(project_factory):
    project = project_factory(type="Mensura")

    create_acc_entry(project, "adv", new_value=Decimal("1000.00"))
    create_acc_entry(project, "exp", new_value=Decimal("300.00"))

    project.refresh_from_db()
    acc = project.account
    assert acc.advance == Decimal("1000.00")
    assert acc.expense == Decimal("300.00")
    assert acc.networth == Decimal("700.00")

    summary = MonthlyFinancialSummary.objects.get(user=project.user)
    assert summary.total_advance == Decimal("1000.00")
    assert summary.total_expenses == Decimal("300.00")
    assert summary.net_worth == Decimal("700.00")
    # income_mensura: +1000 (anticipo) -300 (gasto)
    assert summary.income_mensura == Decimal("700.00")


def test_anticipos_sucesivos_se_acumulan(project_factory):
    project = project_factory()

    create_acc_entry(project, "adv", new_value=Decimal("1000.00"))
    create_acc_entry(project, "adv", new_value=Decimal("500.00"))

    project.refresh_from_db()
    assert project.account.advance == Decimal("1500.00")
    assert AccountMovement.objects.filter(
        account=project.account, movement_type="ADV"
    ).count() == 2


def test_presupuesto_setea_estimated_sin_tocar_networth(project_factory):
    project = project_factory()

    create_acc_entry(project, "est", new_value=Decimal("5000.00"))

    project.refresh_from_db()
    assert project.account.estimated == Decimal("5000.00")
    assert project.account.networth == Decimal("0.00")
