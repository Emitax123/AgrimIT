import logging

from django.db import models
from django.db.models import F
from apps.users.models import User

logger = logging.getLogger(__name__)

# Remove circular import - Project will reference Account via OneToOneField

class Account(models.Model):
    # Remove project field - it will be accessed via reverse relationship
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='accounts')
    estimated = models.DecimalField(max_digits=20, decimal_places=2, default=0.00, verbose_name="Presupuesto")
    expense = models.DecimalField(max_digits=20, decimal_places=2, default=0.00, verbose_name="Gastos")
    advance = models.DecimalField(max_digits=20, decimal_places=2, default=0.00, verbose_name="Anticipos")
    created = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    updated = models.DateTimeField(auto_now=True, verbose_name="Última Actualización")
    
    def __str__(self):
        # Access project through reverse relationship
        if hasattr(self, 'project'):
            return f"Cuenta - {self.project.titular_name}"
        return f"Cuenta #{self.id}"
    @property
    def networth(self):
        """
        Calculate the net worth of the account.

        Net profit: payments received (advance) minus costs incurred (expense).
        Consistent with MonthlyFinancialSummary.net_worth.
        """
        return self.advance - self.expense

    def apply_movement(self, movement):
        """Apply a saved AccountMovement's effect to this account's balances.

        ADV/EXP acumulan sobre el saldo actual; EST fija el presupuesto al
        último valor. Usa F() para una actualización atómica en la base.
        Centraliza lo que antes vivía en ``accounting.views.create_acc_entry``
        (Plan 04, item 2).
        """
        if movement.movement_type == 'ADV':
            Account.objects.filter(pk=self.pk).update(advance=F('advance') + movement.amount)
        elif movement.movement_type == 'EXP':
            Account.objects.filter(pk=self.pk).update(expense=F('expense') + movement.amount)
        elif movement.movement_type == 'EST':
            Account.objects.filter(pk=self.pk).update(estimated=movement.amount)

    class Meta:
        verbose_name = "Cobranza"
        verbose_name_plural = "Cobranzas"
        
class AccountMovement(models.Model):
    MOVEMENT_TYPES = (
        ('ADV', 'Anticipo'),
        ('EXP', 'Gasto'),
        ('EST', 'Presupuesto'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='account_movements')
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='movements')
    # Remove project field - get project through account.project relationship
    amount = models.DecimalField(max_digits=20, decimal_places=2, verbose_name="Monto")  # Increased precision
    movement_type = models.CharField(max_length=3, choices=MOVEMENT_TYPES, verbose_name="Tipo de Movimiento")
    description = models.CharField(max_length=255, blank=True, verbose_name="Descripción")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Creado por")
    class Meta:
        verbose_name = "Movimiento de Cuenta"
        verbose_name_plural = "Movimientos de Cuenta"
        ordering = ['-created_at']  # Default ordering, newest first
        indexes = [
            models.Index(fields=['account', 'created_at']),  # For queries filtering by account and sorting by date
            models.Index(fields=['movement_type']),
            models.Index(fields=['user', 'movement_type']),
            models.Index(fields=['user', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_movement_type_display()} - {self.amount} - {self.created_at.strftime('%d/%m/%Y')}"
    
class MonthlyFinancialSummary(models.Model):
    """
    Model that aggregates financial data by month.
    New instances are created automatically when data is recorded in a new month.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='monthly_summaries', verbose_name="Propietario")
    year = models.IntegerField(verbose_name="Año")
    month = models.IntegerField(verbose_name="Mes")
    total_advance = models.DecimalField(max_digits=20, decimal_places=2, default=0.00, verbose_name="Cobros Total")
    total_expenses = models.DecimalField(max_digits=20, decimal_places=2, default=0.00, verbose_name="Gastos Total")
    

    # Mapa tipo de proyecto -> campo de ganancia neta por categoría.
    INCOME_FIELD_BY_TYPE = {
        'Mensura': 'income_mensura',
        'Estado Parcelario': 'income_est_parc',
        'Amojonamiento': 'income_amoj',
        'Relevamiento': 'income_relev',
        'Legajo Parcelario': 'income_leg',
    }

    income_mensura = models.DecimalField(max_digits=20, decimal_places=2, default=0.00, verbose_name="Ganancia Neta Mensura")
    income_est_parc = models.DecimalField(max_digits=20, decimal_places=2, default=0.00, verbose_name="Ganancia Neta Est Parcelario")
    income_leg = models.DecimalField(max_digits=20, decimal_places=2, default=0.00, verbose_name="Ganancia Neta Legajos")
    income_amoj = models.DecimalField(max_digits=20, decimal_places=2, default=0.00, verbose_name="Ganancia Neta Amojonamiento")
    income_relev = models.DecimalField(max_digits=20, decimal_places=2, default=0.00, verbose_name="Ganancia Neta Relevamiento")
    last_updated = models.DateTimeField(auto_now=True, verbose_name="Última Actualización")

    class Meta:
        verbose_name = "Resumen Mensual"
        verbose_name_plural = "Resumenes Mensuales"
        unique_together = ['user', 'year', 'month']  # Ensure only one record per user/month
        ordering = ['-year', '-month']  # Default ordering, newest first
        indexes = [
            models.Index(fields=['user', 'year', 'month'], name='acc_summary_user_ym_idx'),  # lookups by user/year/month
        ]

    def __str__(self):
        month_names = {
            1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
            5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
            9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
        }
        return f"{month_names.get(self.month, self.month)} - {self.year} - {self.user.username}"
    
    @property
    def net_worth(self):
        """
        Calculate the net worth of the monthly summary.
        Returns total_advance - total_expenses
        """
        return self.total_advance - self.total_expenses
    
    @classmethod
    def record_movement(cls, movement, project_type=None):
        """Agrega un AccountMovement ya guardado al resumen de su mes.

        ADV suma a ``total_advance`` y a la ganancia neta de la categoría del
        proyecto; EXP suma a ``total_expenses`` y resta de la ganancia neta;
        EST no afecta totales. Las actualizaciones usan F() (atómicas).
        El resumen se crea si no existe. Centraliza la lógica que vivía en
        ``accounting.views.create_acc_entry`` (Plan 04, item 2).
        """
        created_at = movement.created_at
        summary, _ = cls.objects.get_or_create(
            user=movement.user,
            year=created_at.year,
            month=created_at.month,
        )

        updates = {}
        income_delta = None
        if movement.movement_type == 'ADV':
            updates['total_advance'] = F('total_advance') + movement.amount
            income_delta = movement.amount
        elif movement.movement_type == 'EXP':
            updates['total_expenses'] = F('total_expenses') + movement.amount
            income_delta = -movement.amount
        # EST: no modifica totales ni ganancia neta.

        if income_delta is not None and project_type:
            income_field = cls.INCOME_FIELD_BY_TYPE.get(project_type)
            if income_field:
                updates[income_field] = F(income_field) + income_delta
            else:
                logger.error(f"Unknown project type: {project_type}. Cannot update summary.")

        if updates:
            cls.objects.filter(pk=summary.pk).update(**updates)
        return summary

    @classmethod
    def initialize(cls, year, month):
        """
        Create a new monthly summary record with default values for the specified year and month.
        If record already exists, it will be returned without modifications.
        """
        
        summary, created = cls.objects.get_or_create(
            year=year,
            month=month,
            defaults={
                'total_advance': 0.00,
                'total_expenses': 0.00,
                'total_networth': 0.00,
            }
        )
        return summary


