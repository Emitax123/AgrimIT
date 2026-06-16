from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from django.utils import timezone
from typing import Optional
import logging
logger = logging.getLogger(__name__)
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.db.models import Q, Sum, Count
from django.db.models.functions import ExtractMonth
from apps.accounting.models import Account, AccountMovement, MonthlyFinancialSummary
from apps.project_admin.models import Project
from apps.users.models import User
from django.contrib.auth.decorators import login_required
from django.db.models import F
from django.db import transaction
from .forms import ManualAccountEntryForm


def get_or_create_account(project: Project) -> tuple[Account, bool]:
    """
    Get or create an account for a project using the project instance.
    
    Args:
        project: The project instance to create an account for.
        
    Returns:
        A tuple containing (account, created) where created is True if a new account was created.
    """
    try:
        # Check if the project already has an account
        if hasattr(project, 'account') and project.account:
            logger.info(f"Account already exists for project {project.id}")
            return project.account, False
        account = Account.objects.create(
            user=project.user,
            estimated=0.00,
            expense=0.00,
            advance=0.00
        )
        project.account = account
        project.save()

        logger.info(f"Account created for project {project.id}")
        return account, True
    
    except Exception as e:
        logger.error(f"Error creating account for project {project.id}: {e}")
        raise
    except Project.DoesNotExist:
        logger.error(f"Project with id {project.id} does not exist")
        raise


def get_or_create_account_by_id(project_id: int) -> tuple[Optional[Account], bool]:
    """
    Get or create an account for a project using the project ID.
    
    Args:
        project_id: The ID of the project to create an account for.
        
    Returns:
        A tuple containing (account, created) where created is True if a new account was created.
        Returns (None, False) if the project doesn't exist.
    """
    try:
        project = get_object_or_404(Project, id=project_id)
        
        return get_or_create_account(project)
    except Project.DoesNotExist:
        logger.error(f"Project with id {project.id} does not exist.")
        return None, False
    except Exception as e:
        logger.error(f"Error creating account for project {project.id}: {e}")
        return None, False

def create_account(project_id: int) -> Optional[Account]: 
    """
    Create an account for a project if it does not already exist.
    
    Args:
        project_id: The ID of the project to create an account for.
        
    Returns:
        The created or existing account, or None if project doesn't exist.
    """
    account, created = get_or_create_account_by_id(project_id)
    return account

_FIELD_TO_MOVEMENT_TYPE = {'adv': 'ADV', 'exp': 'EXP', 'est': 'EST'}


def _coerce_decimal(value) -> Decimal:
    """Convertir cualquier entrada a Decimal; None o valores inválidos -> 0.00."""
    if value is None:
        return Decimal('0.00')
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal('0.00')


def _default_movement_description(field: str, amount: Decimal) -> str:
    """Descripción por defecto del movimiento según el campo y el signo del monto."""
    if field == 'adv':
        return f"Se devolvieron ${abs(amount)}" if amount < 0 else f"Se cobraron ${amount}"
    if field == 'exp':
        return f"Se redujo el gasto en ${abs(amount)}" if amount < 0 else f"Se ingreso el gasto de ${amount}"
    return f"Se ingreso costo final de ${amount}"


def create_acc_entry(project: Project,
                     field: str,
                     old_value: Optional[Decimal] = None,
                     new_value: Optional[Decimal] = None,
                     msg: Optional[str] = None,
                     ) -> Optional[Account]:
    """
    Registra un movimiento de cuenta para un proyecto.

    Crea el ``AccountMovement``; el efecto sobre los saldos del ``Account`` y el
    resumen mensual (``MonthlyFinancialSummary``) lo aplica la señal post_save
    de AccountMovement (``apps/accounting/signals.py``). Plan 04, item 2.

    Args:
        project: El proyecto.
        field: El campo afectado ('adv', 'exp', o 'est').
        old_value: Sin uso (se conserva por compatibilidad de firma).
        new_value: El monto del movimiento.
        msg: Descripción opcional del movimiento.

    Returns:
        El Account actualizado, o None si la operación falló.
    """
    new_value = _coerce_decimal(new_value)

    movement_type = _FIELD_TO_MOVEMENT_TYPE.get(field)
    if movement_type is None:
        logger.error(f"Invalid field type '{field}'")
        return None

    try:
        with transaction.atomic():
            project = get_object_or_404(Project, id=project.id)
            account, _ = get_or_create_account(project)

            description = msg if msg is not None else _default_movement_description(field, new_value)

            AccountMovement.objects.create(
                user=project.user,
                account=account,
                amount=new_value,
                movement_type=movement_type,
                description=description,
            )

        # Reflejar en el objeto en memoria los cambios que la señal persistió.
        account.refresh_from_db()
        return account

    except Project.DoesNotExist:
        logger.error(f"Project with id {project.id} does not exist")
        return None
    except Exception as e:
        logger.error(f"Error in create_acc_entry: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

@login_required
def create_manual_acc_entry (request, pk): 
    """ 
                     
    User can create a manual account entry for a project.
    This function handles two states
    POST handles the data that user send via form, using this data to create a new account movement,
    calling for this the function create_acc_entry()
    if not POST, then renders a template with the previous mentioned form
   
    """
    project = get_object_or_404(Project, id=pk, user=request.user)
    if request.method == 'POST':
        # Handle form submission
        form = ManualAccountEntryForm(request.POST)
        if form.is_valid():
            if form.cleaned_data['movement_type'] == 'ADV':
               type = 'adv'
            else:
                if form.cleaned_data['movement_type'] == 'EXP':
                    type = 'exp'
                else:
                    type = 'est'
                
            # Create the account entry
            create_acc_entry(
                project=project,
                field=type,
                old_value=None,
                new_value=form.cleaned_data['amount'],
                msg=form.cleaned_data.get('description'),  # Use description from form if provided
            )
            if type == 'est':
                # If it's an EST entry, redirect to the accounting display
                return redirect('projectview', pk=project.id)
            return redirect('accounting_display', pk=project.id)
    else:
        # Render the form
        form = ManualAccountEntryForm()

    return render(request, 'accounting/account_form.html', {'form': form, 'project': project})

@login_required
def accounting_mov_display(request: HttpRequest, 
                           pk: Optional[int] = None
                           ) -> HttpResponse:
    """
    Display the accounting information for all projects or for a specific project.
    """
    
   
    
    # If project pk is provided in URL, filter by it
    if pk is not None:

        accounts_query = AccountMovement.objects.select_related(
            'account__project', 'account__project__client').exclude(
                movement_type='EST').filter(
                    user=request.user, account__project__id=pk)
    else:
        # If no project pk is provided, show all movements for the user
        accounts_query = AccountMovement.objects.select_related(
            'account__project', 'account__project__client').exclude(
                movement_type='EST').filter(user=request.user)
    # Apply date filtering if requested
    if request.GET.get('filter') == 'true':
        start_date = request.GET.get('start-date')
        end_date = request.GET.get('end-date')
        
        try:
            # Apply start date filter if provided
            if start_date:
                accounts_query = accounts_query.filter(created_at__gte=start_date)

            # Apply end date filter if provided
            if end_date:
                # Add 1 day to include the entire end date
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
                end_date_next = (end_date_obj + timedelta(days=1)).strftime('%Y-%m-%d')
                accounts_query = accounts_query.filter(created_at__lt=end_date_next)
        except ValueError:
            # Handle invalid date format gracefully
            # Just continue without applying the filter
            pass
    
    # Get the final queryset ordered by date (newest first)
    accounts_mov = accounts_query.order_by('-created_at')

    # Pass the filter parameters to the template context to maintain state
    context = {
        'accounts_mov': accounts_mov,
        'start_date': request.GET.get('start-date', ''),
        'end_date': request.GET.get('end-date', ''),
        'project_id': pk  # Pass the project ID to the template
    }

    # Cuentas por cobrar con aging (§7.3): solo en la vista global (sin proyecto puntual).
    if pk is None:
        receivables = get_receivables(request.user)
        context['receivables'] = receivables
        context['receivables_count'] = receivables['count']

    return render(request, 'accounting/accounting_history.html', context)

def get_monthly_networth_data(year: int, user: User) -> tuple[list, list]:
    """
    Get monthly net worth data for chart visualization.
    OPTIMIZED: Uses single query with annotate for calculated net worth.
    
    Args:
        year: The year to get monthly data for.
        user: The user to filter data for.
        
    Returns:
        A tuple containing (month_labels, networth_values) for the specified year.
    """
    # OPTIMIZATION 1: Single query with annotate to calculate net_worth in database
    # Instead of accessing summary.net_worth (which may trigger additional queries),
    # we calculate it directly in the database using F() expressions
    year_summaries = MonthlyFinancialSummary.objects.filter(
        year=year,
        user=user  # Filter by user
    ).annotate(
        calculated_net_worth=F('total_advance') - F('total_expenses')
    ).values('month', 'calculated_net_worth').order_by('month')
    
    # OPTIMIZATION 2: Create lookup dictionary in single pass
    # Convert QuerySet to dict for O(1) lookup instead of O(n) iteration
    summary_by_month = {
        item['month']: float(item['calculated_net_worth'] or 0)
        for item in year_summaries
    }
    
    # OPTIMIZATION 3: Use list comprehension for better performance
    # Generate month labels and values in single pass instead of separate loops
    month_labels = [month_str_short(month_num) for month_num in range(1, 13)]
    networth_values = [
        summary_by_month.get(month_num, 0.0) 
        for month_num in range(1, 13)
    ]
    
    return month_labels, networth_values

#---------------------

def month_str(number):
    months = {
        1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
        5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
        9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
    }

    return months.get(number, 'Mes no válido')

def month_str_short(number):
    """
    Returns short month names for chart labels to avoid overlapping.
    """
    months = {
        1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr',
        5: 'May', 6: 'Jun', 7: 'Jul', 8: 'Ago',
        9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic'
    }

    return months.get(number, 'Mes no válido')

def format_currency(value):
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def pesos(value) -> str:
    """Formato es-AR sin decimales: 1234567 -> '1.234.567' (separador de miles con punto)."""
    try:
        n = int(round(float(value or 0)))
    except (TypeError, ValueError):
        n = 0
    return f"{n:,}".replace(",", ".")

def chart_data_format(data: dict) -> dict:
    """
    Format data for chart visualization.
    This function processes raw financial data into a structured format suitable for 
    rendering charts, specifically doughnut charts. It organizes data into two main categories:
    monthly net worth progression and revenue by service type.
    Parameters:
    -----------
    data : dict
        A dictionary containing financial data with a 'raw' key that includes:
        - 'estimated': Total estimated revenue
        - 'advance': Amount collected/advanced
        - 'expense': Total expense
        - 'net_by_type': Dictionary with revenue breakdown by service type:
            - 'estado_parcelario': Revenue from property status services
            - 'amojonamiento': Revenue from boundary marking services
            - 'relevamiento': Revenue from surveying services
            - 'mensura': Revenue from measurement services
            - 'legajo_parcelario': Revenue from property file services
        - 'monthly_data': Dictionary with monthly net worth data:
            - 'labels': Month names
            - 'values': Net worth values for each month
    Returns:
    --------
    dict
        A formatted dictionary containing:
        - 'label1', 'label2': Chart titles/labels
        - 'labels1', 'labels2': Category labels for the two chart types
        - 'values1', 'values2': Corresponding numerical values for each category
        - 'chart_type': The type of chart to render (doughnut)
        - 'barckgroundColor', 'barckgroundColor2': Color schemes for the charts
    """
    
    chart_data = {
        'label1': 'Ganancia Neta Mensual',
        'label2': 'Ganancias por tipo',
        'labels1': data['raw']['monthly_data']['labels'],
        'values1': data['raw']['monthly_data']['values'],
        'labels2': ['Est.Parcelario', 'Amojonamiento', 'Relevamiento', 'Mensura', 'Legajo Parcelario'],
        'values2': [
            float(data['raw']['net_by_type']['estado_parcelario']),
            float(data['raw']['net_by_type']['amojonamiento']),
            float(data['raw']['net_by_type']['relevamiento']),
            float(data['raw']['net_by_type']['mensura']),
            float(data['raw']['net_by_type']['legajo_parcelario'])
        ],
        'chart_type': 'doughnut',
        'barckgroundColor': ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40', '#FF6384', '#C9CBCF', '#4BC0C0', '#FF6384', '#C9CBCF', '#36A2EB'],
        'barckgroundColor2': ['red', 'blue', 'green', 'orange', 'purple']
    }
    return chart_data

# charts/views.py
@login_required
def chart_data(request: HttpRequest) -> JsonResponse:
    try:
        if request.method == 'POST':
            # Try to get date from POST data
            date = request.POST.get('date')       
            # If we got a date and it's in YYYY-MM format
            if date and '-' in date:
                try:
                    date_split = date.split("-")
                    if len(date_split) >= 2:
                        month = int(date_split[1])
                        year = int(date_split[0])
                    else:
                        raise ValueError(f"Invalid date format: {date}")
                except Exception as e:
                    month = datetime.now().month
                    year = datetime.now().year
            else:
                month = datetime.now().month
                year = datetime.now().year
        else:
            month = datetime.now().month
            year = datetime.now().year

        # Get monthly net worth data for the year - FILTERED BY USER
        month_labels, networth_values = get_monthly_networth_data(year, request.user)
            
        month_summary = MonthlyFinancialSummary.objects.filter(
            year=year, 
            month=month, 
            user=request.user  # Filter by user
        ).first()
        total_estimated = 0
        sums = Account.objects.filter(
            project__created__month=month, 
            project__created__year=year,
            user=request.user  # Filter by user
        ).aggregate(
            total_estimated=Sum('estimated')
        )
        total_estimated = sums['total_estimated'] or 0
    
        
        if month_summary:
            total_advance = month_summary.total_advance or 0
            total_expenses = month_summary.total_expenses or 0
            net_estado_parcelario = month_summary.income_est_parc or 0
            net_mensura = month_summary.income_mensura or 0
            net_amojonamiento = month_summary.income_amoj or 0
            net_relevamiento = month_summary.income_relev or 0
            net_legajo_parcelario = month_summary.income_leg or 0
        else:
            total_advance = 0
            total_expenses = 0
            net_estado_parcelario = 0
            net_mensura = 0
            net_amojonamiento = 0
            net_relevamiento = 0
            net_legajo_parcelario = 0
            
    except Exception as e:
        # Fall back to default values if there's an error
        month_labels = [month_str_short(i) for i in range(1, 13)]
        networth_values = [0] * 12
        total_advance = 0
        total_expenses = 0
        net_estado_parcelario = 0
        net_mensura = 0
        net_amojonamiento = 0
        net_relevamiento = 0
        net_legajo_parcelario = 0
        
    
    # Chart 1: Monthly Net Worth
    labels = month_labels
    values = networth_values
    backg = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40', '#FF6384', '#C9CBCF', '#4BC0C0', '#FF6384', '#C9CBCF', '#36A2EB']

    # Chart 2: Revenue by type (unchanged)
    labels2 = ['Est.Parcelario', 'Amojonamiento', 'Relevamiento', 'Mensura', 'Legajo Parcelario']
    values2 = [net_estado_parcelario, net_amojonamiento, net_relevamiento, net_mensura, net_legajo_parcelario]
    backg2 = ['red', 'blue', 'green', 'orange', 'purple']

    chart_data = {
        'label1': 'Ganancia Neta Mensual',
        'label2': 'Ganancias por tipo',
        
        'labels2': labels2,
        'values2': values2,
        'labels1': labels,
        'values1': values,
        'chart_type': 'doughnut',
        'barckgroundColor':backg,
        'barckgroundColor2':backg2,
    }
    
    return JsonResponse(chart_data)

#Calculo de los meses a mostrar
def generate_month_data(months: list, year: list) -> tuple[list, list]:
    current_year = datetime.now().year
    current_month = datetime.now().month
    
    for y in range(2023, current_year + 1):
        year.append({'year':y})
        end_month = 12 if y < current_year else current_month
        for m in range(1, end_month + 1):
            months.append({'year': y, 'month': m})

    return months, year

def get_financial_data(year: int, month: int, user: User) -> dict:
    """
    Single function to retrieve all financial data needed for both
    balance and chart displays.
    """
    data = {
        'raw': {},
        'formatted': {},
        'counts': {},
        'objects': {},
    }
    
    # 1. Get monthly summary (single query) - FILTERED BY USER
    monthly_summary = MonthlyFinancialSummary.objects.filter(
        year=year, 
        month=month, 
        user=user  # Filter by user
    ).first()
    data['objects']['monthly_summary'] = monthly_summary
    
    # If no monthly summary exists, return empty data structure instead of False
    if not monthly_summary:
        return {
            'raw': {
                'advance': 0,
                'expenses': 0,
                'networth': 0,
                'estimated': 0,
                'pending': 0,
                'net_by_type': {
                    'estado_parcelario': 0,
                    'mensura': 0,
                    'amojonamiento': 0,
                    'relevamiento': 0,
                    'legajo_parcelario': 0,
                }
            },
            'formatted': {
                'total': '$0.00',
                'adv': '$0.00',
                'exp': '$0.00',
                'net': '$0.00',
                'pending': '$0.00',
            },
            'counts': {
                'total': 0,
                'current_month': 0,
                'previous_months': 0,
            },
            'objects': {
                'monthly_summary': None,
                'projects': Project.objects.none(),
                'accounts': Account.objects.none(),
            }
        }
    
    # 2. Get projects (single query) - FILTERED BY USER
    projects = Project.objects.filter(
        created__month=month, 
        created__year=year, 
        user=user  # Filter by user
    )
    data['objects']['projects'] = projects
    
    # 3. Get accounts (single query) - FILTERED BY USER
    accounts = Account.objects.filter(
        project__created__month=month, 
        project__created__year=year,
        user=user  # Filter by user
    )
    data['objects']['accounts'] = accounts
    # 4. Calculate all values once
    if monthly_summary:
        adv = monthly_summary.total_advance or 0
        exp = monthly_summary.total_expenses or 0
        net_estado_parcelario = monthly_summary.income_est_parc or 0
        net_mensura = monthly_summary.income_mensura or 0
        net_amojonamiento = monthly_summary.income_amoj or 0
        net_relevamiento = monthly_summary.income_relev or 0
        net_legajo_parcelario = monthly_summary.income_leg or 0
    else:
        adv = exp = 0
        net_estado_parcelario = net_mensura = net_amojonamiento = 0
        net_relevamiento = net_legajo_parcelario = 0
    
    # 5. Calculate estimated amount (single aggregation)
    sums = accounts.aggregate(total=Sum('estimated'))
    total_estimated = sums['total'] or 0
    
    # 6. Get monthly net worth data for the year - FILTERED BY USER
    month_labels, networth_values = get_monthly_networth_data(year, user)
    
    # Store raw values
    data['raw'] = {
        'advance': adv,
        'expenses': exp,
        'networth': adv - exp,
        'estimated': total_estimated,
        'pending': total_estimated - adv - exp,
        'net_by_type': {
            'estado_parcelario': net_estado_parcelario,
            'mensura': net_mensura,
            'amojonamiento': net_amojonamiento,
            'relevamiento': net_relevamiento,
            'legajo_parcelario': net_legajo_parcelario,
        },
        'monthly_data': {
            'labels': month_labels,
            'values': networth_values,
        }
    }
    
    # Store formatted values
    data['formatted'] = {
        'adv': format_currency(adv),
        'exp': format_currency(exp),
        'net': format_currency(adv-exp),
        'total': format_currency(total_estimated),
        'pending': format_currency(total_estimated - adv - exp),
    }
    
    # Store counts - FILTERED BY USER
    data['counts'] = {
        'total': projects.count(),
        'current_month': projects.filter(created__month=month).count(),
        
        'previous_months': Project.objects.filter(
            closed=False, 
            user=user  # Filter by user
        ).exclude(
            Q(created__year=year, created__month=month)
        ).count(),
    }
    
    return data

#Funcion usada dentro de balance, para mostrar el balance anual
def balance_anual(year: int, user: User) -> tuple[list, list]:
    # Annotate each project with its month
    
    year_summary = MonthlyFinancialSummary.objects.filter(
        year=year, 
        user=user  # Filter by user
    ).order_by('month')
    # Create a dictionary to easily look up summaries by month
    summary_by_month = {summary.month: summary for summary in year_summary}
    
    # Pre-fetch all project counts for the year to avoid multiple queries - FILTERED BY USER
    project_counts = {}
    for month_data in Project.objects.filter(
        created__year=year, 
        user=user  # Filter by user
    ).annotate(
        month=ExtractMonth('created')
    ).values('month').annotate(count=Count('id')):
        project_counts[month_data['month']] = month_data['count']
    
    monthly_totals = []
    year_networth = 0
    for month_num in range(1, 13):
        # Get the summary for the current month, or create a default one if it doesn't exist
        month_name = month_str(month_num)
        if month_num in summary_by_month:
            #Find data for month, because it exists
            summary = summary_by_month[month_num]
            
            monthly_totals.append({
                'month': month_str(summary.month),
                'total_networth': pesos(summary.net_worth),
                'net_raw': float(summary.net_worth or 0),
                'project_count': project_counts.get(month_num, 0)
            })
            year_networth += summary.net_worth
        else:
            # If no summary exists for this month, create a default one
            monthly_totals.append({
                'month': month_name,
                'total_networth': pesos(0),
                'net_raw': 0.0,
                'project_count': project_counts.get(month_num, 0)
            })
    return monthly_totals, pesos(year_networth)

# ---------------------------------------------------------------------------
# Helpers de finanzas (Fase 3 — REDESIGN §7.1, §7.2, §7.5, §7.6, §7.3)
# ---------------------------------------------------------------------------

# Clave de tipo (querystring) -> columna neta por tipo en MonthlyFinancialSummary.
INCOME_FIELD_BY_TIPO = {
    'mensura': 'income_mensura',
    'est_parc': 'income_est_parc',
    'amoj': 'income_amoj',
    'relev': 'income_relev',
    'leg': 'income_leg',
}
# Clave de tipo -> etiqueta visible.
TIPO_LABELS = {
    'mensura': 'Mensuras',
    'est_parc': 'Est. Parcelarios',
    'amoj': 'Amojonamientos',
    'relev': 'Relevamientos',
    'leg': 'Legajos',
}
# Clave de tipo -> valor de Project.type (para contar proyectos facturados por tipo).
TIPO_TO_PROJECT_TYPE = {
    'mensura': 'Mensura',
    'est_parc': 'Estado Parcelario',
    'amoj': 'Amojonamiento',
    'relev': 'Relevamiento',
    'leg': 'Legajo Parcelario',
}


def _prev_year_month(year: int, month: int) -> tuple[int, int]:
    """Mes/año anterior, manejando el salto enero -> diciembre del año previo."""
    if month == 1:
        return year - 1, 12
    return year, month - 1


def _count_facturados(user: User, year: int, month: int, project_type: Optional[str] = None) -> int:
    """Proyectos del usuario con al menos un movimiento ADV en el mes (opcional por tipo)."""
    qs = Project.objects.filter(
        user=user,
        account__movements__movement_type='ADV',
        account__movements__created_at__year=year,
        account__movements__created_at__month=month,
    )
    if project_type:
        qs = qs.filter(type=project_type)
    return qs.distinct().count()


def get_balance_kpis(user: User, year: int, month: int, tipo: Optional[str] = None) -> dict:
    """
    KPIs comparativos del mes vs el mes anterior (§7.1).

    Devuelve un dict con 'ingresos', 'gastos', 'neto', 'facturados' (cada uno con
    value_fmt, delta_str, up, good, has_prev) y 'prev_month_label'. Para gastos,
    'good' es True cuando bajan. Con `tipo` activo solo se computa el neto del tipo
    (Ingresos/Gastos brutos quedan sin desglose, §7.5).
    """
    prev_year, prev_month = _prev_year_month(year, month)
    cur = MonthlyFinancialSummary.objects.filter(user=user, year=year, month=month).first()
    prev = MonthlyFinancialSummary.objects.filter(user=user, year=prev_year, month=prev_month).first()

    def _pct_kpi(actual, anterior, good_when_up=True):
        actual = Decimal(str(actual or 0))
        anterior = Decimal(str(anterior or 0))
        if anterior != 0:
            pct = (actual - anterior) / abs(anterior) * 100
            up = actual >= anterior
            return {
                'value_fmt': pesos(actual),
                'delta_str': f"{abs(pct):.1f}".replace('.', ','),
                'up': up,
                'good': (up if good_when_up else not up),
                'has_prev': True,
            }
        return {'value_fmt': pesos(actual), 'delta_str': None,
                'up': None, 'good': None, 'has_prev': False}

    cur_adv = (cur.total_advance if cur else 0) or 0
    cur_exp = (cur.total_expenses if cur else 0) or 0
    prev_adv = (prev.total_advance if prev else 0) or 0
    prev_exp = (prev.total_expenses if prev else 0) or 0

    if tipo and tipo in INCOME_FIELD_BY_TIPO:
        col = INCOME_FIELD_BY_TIPO[tipo]
        cur_net = getattr(cur, col, 0) if cur else 0
        prev_net = getattr(prev, col, 0) if prev else 0
        ptype = TIPO_TO_PROJECT_TYPE[tipo]
        neto = _pct_kpi(cur_net, prev_net, good_when_up=True)
        # Sin desglose bruto por tipo: marcar Ingresos/Gastos como no disponibles.
        sin_desglose = {'value_fmt': '—', 'delta_str': None, 'up': None,
                        'good': None, 'has_prev': False, 'no_desglose': True}
        ingresos = dict(sin_desglose)
        gastos = dict(sin_desglose)
    else:
        ptype = None
        ingresos = _pct_kpi(cur_adv, prev_adv, good_when_up=True)
        gastos = _pct_kpi(cur_exp, prev_exp, good_when_up=False)
        neto = _pct_kpi(Decimal(str(cur_adv)) - Decimal(str(cur_exp)),
                        Decimal(str(prev_adv)) - Decimal(str(prev_exp)), good_when_up=True)

    cur_fact = _count_facturados(user, year, month, ptype)
    prev_fact = _count_facturados(user, prev_year, prev_month, ptype)
    diff = cur_fact - prev_fact
    facturados = {
        'value_fmt': cur_fact,
        'delta_str': (f"+{diff}" if diff > 0 else (str(diff) if diff < 0 else None)),
        'up': (diff > 0 if diff != 0 else None),
        'good': (diff > 0 if diff != 0 else None),
        'has_prev': diff != 0,
    }

    return {
        'ingresos': ingresos,
        'gastos': gastos,
        'neto': neto,
        'facturados': facturados,
        'prev_month_label': month_str(prev_month),
    }


def get_monthly_income_expense(year: int, user: User, tipo: Optional[str] = None) -> dict:
    """
    Series mensuales para el gráfico anual (§7.6). Sin tipo: ingresos/gastos brutos
    + neto acumulado. Con tipo: el neto de ese tipo por mes (gastos en cero, §7.5).
    """
    if tipo and tipo in INCOME_FIELD_BY_TIPO:
        col = INCOME_FIELD_BY_TIPO[tipo]
        rows = MonthlyFinancialSummary.objects.filter(year=year, user=user).values('month', col)
        net_by_month = {r['month']: float(r[col] or 0) for r in rows}
        labels, ingresos, neto_acum = [], [], []
        acc = 0.0
        for m in range(1, 13):
            labels.append(month_str_short(m))
            n = net_by_month.get(m, 0.0)
            ingresos.append(n)
            acc += n
            neto_acum.append(round(acc, 2))
        return {'labels': labels, 'ingresos': ingresos, 'gastos': [0.0] * 12,
                'neto_acum': neto_acum, 'mode': 'tipo', 'tipo_label': TIPO_LABELS[tipo]}

    rows = MonthlyFinancialSummary.objects.filter(year=year, user=user)\
        .values('month', 'total_advance', 'total_expenses')
    adv_by_month = {r['month']: float(r['total_advance'] or 0) for r in rows}
    exp_by_month = {r['month']: float(r['total_expenses'] or 0) for r in rows}
    labels, ingresos, gastos, neto_acum = [], [], [], []
    acc = 0.0
    for m in range(1, 13):
        labels.append(month_str_short(m))
        i = adv_by_month.get(m, 0.0)
        g = exp_by_month.get(m, 0.0)
        ingresos.append(i)
        gastos.append(g)
        acc += (i - g)
        neto_acum.append(round(acc, 2))
    return {'labels': labels, 'ingresos': ingresos, 'gastos': gastos,
            'neto_acum': neto_acum, 'mode': 'bruto', 'tipo_label': None}


def get_top_clients(user: User, year: int, n: int = 5) -> list:
    """
    Top N clientes por facturación (movimientos ADV) del año (§7.6).
    Cada item: {name, projects_count, total, total_fmt, pct} (pct sobre el máximo).
    """
    rows = (AccountMovement.objects
            .filter(user=user, movement_type='ADV', created_at__year=year)
            .values('account__project__client', 'account__project__client__name')
            .annotate(total=Sum('amount'),
                      projects_count=Count('account__project', distinct=True))
            .order_by('-total'))
    result = []
    for r in rows:
        if r['account__project__client'] is None:
            continue
        total = r['total'] or Decimal('0.00')
        result.append({
            'name': r['account__project__client__name'] or '—',
            'projects_count': r['projects_count'],
            'total': total,
            'total_fmt': pesos(total),
        })
        if len(result) >= n:
            break
    max_total = max((float(r['total']) for r in result), default=0.0) or 1.0
    for r in result:
        r['pct'] = round(float(r['total']) / max_total * 100, 1)
    return result


def get_receivables(user: User) -> dict:
    """
    Cuentas por cobrar con aging (§7.3). Considera proyectos NO cerrados con
    estimated > 0 y saldo (estimated − advance) > 0. La antigüedad se mide desde el
    último movimiento ADV de la cuenta, o desde project.created si nunca cobró.
    Devuelve {rows, buckets, total, total_fmt, count}.
    """
    accounts = (Account.objects
                .filter(project__user=user, project__closed=False, estimated__gt=0)
                .annotate(saldo=F('estimated') - F('advance'))
                .filter(saldo__gt=0)
                .select_related('project', 'project__client'))
    today = timezone.now().date()
    buckets = {
        'al_dia': {'total': Decimal('0.00'), 'count': 0},
        'b30_60': {'total': Decimal('0.00'), 'count': 0},
        'b60_90': {'total': Decimal('0.00'), 'count': 0},
        'b90': {'total': Decimal('0.00'), 'count': 0},
    }
    rows = []
    total = Decimal('0.00')
    for acc in accounts:
        project = acc.project
        last_adv = (AccountMovement.objects
                    .filter(account=acc, movement_type='ADV')
                    .order_by('-created_at').first())
        last_date = last_adv.created_at if last_adv else None
        ref_date = last_date.date() if last_date else project.created.date()
        days = (today - ref_date).days
        saldo = acc.saldo
        total += saldo
        if days < 30:
            key = 'al_dia'
        elif days < 60:
            key = 'b30_60'
        elif days < 90:
            key = 'b60_90'
        else:
            key = 'b90'
        buckets[key]['total'] += saldo
        buckets[key]['count'] += 1
        rows.append({
            'project': project,
            'client': project.client,
            'last_payment_date': last_date,
            'saldo': saldo,
            'saldo_fmt': pesos(saldo),
            'days': days,
        })
    rows.sort(key=lambda r: r['days'], reverse=True)
    for b in buckets.values():
        b['total_fmt'] = pesos(b['total'])
    return {
        'rows': rows,
        'buckets': buckets,
        'total': total,
        'total_fmt': pesos(total),
        'count': len(rows),
    }


#Balance
@login_required
def balance(request: HttpRequest) -> HttpResponse:
    """
    Balances (REDESIGN §4.6, §7.1/§7.2/§7.5/§7.6).

    Acepta el mes/año por GET (?year=&month=, navegación con flechas §7.2) y mantiene
    compatibilidad con el POST `date` (YYYY-MM) histórico. Filtro por tipo de trabajo
    vía GET ?tipo= (§7.5). Default: mes/año actual.
    """
    now = datetime.now()
    method_post = False
    non_exist = False

    if request.method == 'POST':
        method_post = True
        date = request.POST.get('date') or ''
        date_split = date.split("-")
        try:
            year = int(date_split[0])
            month = int(date_split[1])
        except (IndexError, ValueError):
            year, month = now.year, now.month
    else:
        try:
            year = int(request.GET.get('year', now.year))
            month = int(request.GET.get('month', now.month))
        except (TypeError, ValueError):
            year, month = now.year, now.month
        if not 1 <= month <= 12:
            year, month = now.year, now.month

    # Tipo de trabajo activo (None = "Todos los tipos").
    tipo = request.GET.get('tipo')
    if tipo not in INCOME_FIELD_BY_TIPO:
        tipo = None

    # Navegación de mes (flechas ‹ ›) y deshabilitar el avance si es el mes actual.
    prev_year, prev_month = _prev_year_month(year, month)
    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)
    next_disabled = (year > now.year) or (year == now.year and month >= now.month)

    kpis = chart_tipo = None
    monthly_totals, year_total, top_clients = [], pesos(0), []
    chart_anual = get_monthly_income_expense(year, request.user, tipo)
    try:
        balance_data = get_financial_data(year, month, request.user)
        monthly_totals, year_total = balance_anual(year, request.user)
        top_clients = get_top_clients(request.user, year)
        kpis = get_balance_kpis(request.user, year, month, tipo)
        non_exist = balance_data['objects']['monthly_summary'] is None
        nbt = balance_data['raw']['net_by_type']
        chart_tipo = {
            'labels': ['Mensuras', 'Est. Parcelarios', 'Amojonamientos', 'Relevamientos', 'Legajos'],
            'values': [
                float(nbt['mensura']), float(nbt['estado_parcelario']),
                float(nbt['amojonamiento']), float(nbt['relevamiento']),
                float(nbt['legajo_parcelario']),
            ],
        }
    except Exception as e:
        logger.error(f"Error al obtener datos financieros del balance: {e}")
        non_exist = True

    top_max = max((float(c['total']) for c in top_clients), default=0.0)

    return render(request, 'accounting/balance.html', {
        'method_post': method_post,
        'month': month_str(month),
        'month_number': month,
        'year': year,
        'tipo': tipo,
        'tipo_labels': TIPO_LABELS,
        'prev_year': prev_year, 'prev_month': prev_month,
        'next_year': next_year, 'next_month': next_month,
        'next_disabled': next_disabled,
        'kpis': kpis,
        'chart_anual': chart_anual,
        'chart_tipo': chart_tipo,
        'top_clients': top_clients,
        'top_max': top_max,
        'monthly_totals': monthly_totals,
        'neto_anual': year_total,
        'non_exist': non_exist,
    })
    
    
@login_required
def balance_info(request: HttpRequest) -> JsonResponse:
    """
    Return balance information for AJAX requests.
    
    Args:
        request: HTTP request containing date information.
        
    Returns:
        JsonResponse: Balance information data in JSON format.
    """
    try:
        if request.method == 'POST':
            date = request.POST.get('date')
            if date and '-' in date:
                try:
                    date_split = date.split("-")
                    if len(date_split) >= 2:
                        month = int(date_split[1])
                        year = int(date_split[0])
                    else:
                        raise ValueError(f"Invalid date format: {date}")
                except Exception as e:
                    month = datetime.now().month
                    year = datetime.now().year
            else:
                month = datetime.now().month
                year = datetime.now().year
        else:
            month = datetime.now().month
            year = datetime.now().year
        
        # Use the existing function to get financial data - FILTERED BY USER
        balance_data = get_financial_data(year, month, request.user)
        if balance_data is False:
            return JsonResponse({'error': 'No financial data found for the specified month and year.'}, status=404)
        # Format the data for the response
        response_data = {
            'balance_info': {
                'month': month_str(month),
                'year': year,
                'total': balance_data['formatted']['total'],
                'adv': balance_data['formatted']['adv'],
                'pending': balance_data['formatted']['pending'],
                'cant_actual_month': balance_data['counts']['current_month'],
                'cant_previus_months': balance_data['counts']['previous_months'],
                'gastos': balance_data['formatted']['exp'],
                'net': balance_data['formatted']['net']
            }
        }
        
        return JsonResponse(response_data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def create_account_with_initial_values(project: Project, 
                                     initial_advance: Decimal = Decimal('0.00'),
                                     initial_expense: Decimal = Decimal('0.00'),
                                     initial_estimated: Decimal = Decimal('0.00')) -> Account:
    """
    Create an account for a project with initial values.
    
    Args:
        project: The project instance to create an account for.
        initial_advance: Initial advance amount (default: 0.00).
        initial_expense: Initial expenses amount (default: 0.00).
        initial_estimated: Initial estimated amount (default: 0.00).
        
    Returns:
        The created account instance.
    """
    try:
        with transaction.atomic():
            account, created = get_or_create_account(project)
            
            if created:
                # Set initial values for new account
                account.advance = initial_advance
                account.expense = initial_expense
                account.estimated = initial_estimated
            
                account.save()
                
                logger.info(f"Account created with initial values for project {project.id}")
            else:
                logger.debug(f"Account already exists for project {project.id}, not updating values")
            
            return account
    except Exception as e:
        logger.error(f"Error creating account with initial values for project {project.id}: {e}")
        raise


def bulk_create_accounts(projects: list[Project]) -> list[Account]:
    """
    Create accounts for multiple projects efficiently.
    
    Args:
        projects: List of project instances to create accounts for.
        
    Returns:
        List of created/existing account instances.
    """
    accounts = []

    try:
        with transaction.atomic():
            for project in projects:
                account, created = get_or_create_account(project)
                accounts.append(account)

            logger.info(f"Processed {len(accounts)} accounts for {len(projects)} projects")
            return accounts
    except Exception as e:
        logger.error(f"Error bulk creating accounts: {e}")
        raise


# ---------------------------------------------------------------------------
# Fase 4 — Factura no oficial (§7.7) y exportes Excel/PDF (§7.4)
# ---------------------------------------------------------------------------

@login_required
def invoice_view(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Factura no oficial de un proyecto (REDESIGN §7.7). Página standalone imprimible.
    Ownership owner-only, consistente con project_view.
    """
    from apps.users.models import StudioProfile

    project = get_object_or_404(
        Project.objects.select_related('account', 'client', 'user'),
        pk=pk, user=request.user,
    )
    account, _ = get_or_create_account(project)
    studio, _ = StudioProfile.objects.get_or_create(user=request.user)
    adv_movs = account.movements.filter(movement_type='ADV').order_by('created_at')

    now = timezone.now()
    context = {
        'project': project,
        'client': project.client,
        'account': account,
        'studio': studio,
        'adv_movs': adv_movs,
        'estimated': account.estimated,
        'total_pagos': account.advance,
        'saldo': account.estimated - account.advance,
        'doc_num': f"{project.pk:04d}-{now.year}",
        'fecha': now,
    }
    return render(request, 'accounting/invoice.html', context)


def _xlsx_response(workbook, filename: str) -> HttpResponse:
    """Serializa un workbook openpyxl a una HttpResponse de descarga."""
    from io import BytesIO
    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
def export_balance_xlsx(request: HttpRequest) -> HttpResponse:
    """Export del balance anual a Excel (§7.4). GET ?year=Y."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment

    now = datetime.now()
    try:
        year = int(request.GET.get('year', now.year))
    except (TypeError, ValueError):
        year = now.year

    monthly_totals, _ = balance_anual(year, request.user)
    series = get_monthly_income_expense(year, request.user)

    wb = Workbook()
    ws = wb.active
    ws.title = f"Balance {year}"

    header_fill = PatternFill(start_color='2D72BA', end_color='2D72BA', fill_type='solid')
    header_font = Font(color='FFFFFF', bold=True)
    money_fmt = '#,##0'

    ws['A1'] = f"AgrimIT — Balance {year}"
    ws['A1'].font = Font(bold=True, size=14, color='2D72BA')

    headers = ['Mes', 'Proyectos', 'Ingresos', 'Gastos', 'Neto']
    header_row = 3
    for col, title in enumerate(headers, start=1):
        cell = ws.cell(row=header_row, column=col, value=title)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center')

    tot_proj = tot_ing = tot_gas = tot_net = 0
    for i, mt in enumerate(monthly_totals):
        r = header_row + 1 + i
        ingresos = series['ingresos'][i]
        gastos = series['gastos'][i]
        neto = mt['net_raw']
        proj = mt['project_count']
        ws.cell(row=r, column=1, value=mt['month'])
        ws.cell(row=r, column=2, value=proj)
        c_ing = ws.cell(row=r, column=3, value=round(ingresos))
        c_gas = ws.cell(row=r, column=4, value=round(gastos))
        c_net = ws.cell(row=r, column=5, value=round(neto))
        for c in (c_ing, c_gas, c_net):
            c.number_format = money_fmt
        tot_proj += proj
        tot_ing += ingresos
        tot_gas += gastos
        tot_net += neto

    total_row = header_row + 1 + len(monthly_totals)
    ws.cell(row=total_row, column=1, value='Total').font = Font(bold=True)
    ws.cell(row=total_row, column=2, value=tot_proj).font = Font(bold=True)
    for col, val in ((3, tot_ing), (4, tot_gas), (5, tot_net)):
        c = ws.cell(row=total_row, column=col, value=round(val))
        c.number_format = money_fmt
        c.font = Font(bold=True)

    widths = [14, 12, 16, 16, 16]
    for col, w in enumerate(widths, start=1):
        ws.column_dimensions[chr(64 + col)].width = w

    return _xlsx_response(wb, f"agrimit_balance_{year}.xlsx")


@login_required
def export_movements_xlsx(request: HttpRequest) -> HttpResponse:
    """Export de movimientos + cuentas por cobrar a Excel (§7.4). GET ?start=&end=."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment

    header_fill = PatternFill(start_color='2D72BA', end_color='2D72BA', fill_type='solid')
    header_font = Font(color='FFFFFF', bold=True)
    money_fmt = '#,##0'

    movs = (AccountMovement.objects
            .select_related('account__project', 'account__project__client')
            .exclude(movement_type='EST')
            .filter(user=request.user))

    start_date = request.GET.get('start')
    end_date = request.GET.get('end')
    try:
        if start_date:
            movs = movs.filter(created_at__gte=start_date)
        if end_date:
            end_next = (datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
            movs = movs.filter(created_at__lt=end_next)
    except ValueError:
        pass
    movs = movs.order_by('-created_at')

    type_labels = {'ADV': 'Anticipo', 'EXP': 'Gasto'}

    wb = Workbook()
    ws = wb.active
    ws.title = 'Movimientos'
    headers = ['Proyecto', 'Cliente', 'Movimiento', 'Monto', 'Fecha']
    for col, title in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col, value=title)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center')
    for i, m in enumerate(movs, start=2):
        project = m.account.project if m.account_id else None
        client = project.client if project else None
        ws.cell(row=i, column=1, value=(f"#{project.pk} {project.type}" if project else '—'))
        ws.cell(row=i, column=2, value=(client.name if client else '—'))
        ws.cell(row=i, column=3, value=type_labels.get(m.movement_type, m.movement_type))
        c_amount = ws.cell(row=i, column=4, value=round(float(m.amount)))
        c_amount.number_format = money_fmt
        ws.cell(row=i, column=5, value=timezone.localtime(m.created_at).strftime('%d/%m/%Y'))
    for col, w in enumerate((22, 22, 14, 16, 14), start=1):
        ws.column_dimensions[chr(64 + col)].width = w

    # Hoja 2: Por cobrar (aging)
    receivables = get_receivables(request.user)
    ws2 = wb.create_sheet('Por cobrar')
    bucket_labels = [
        ('al_dia', 'Al día (<30)'),
        ('b30_60', '30-60 días'),
        ('b60_90', '60-90 días'),
        ('b90', '+90 días'),
    ]
    ws2.cell(row=1, column=1, value='Antigüedad').font = header_font
    ws2.cell(row=1, column=1).fill = header_fill
    ws2.cell(row=1, column=2, value='Proyectos').font = header_font
    ws2.cell(row=1, column=2).fill = header_fill
    ws2.cell(row=1, column=3, value='Total').font = header_font
    ws2.cell(row=1, column=3).fill = header_fill
    for i, (key, label) in enumerate(bucket_labels, start=2):
        b = receivables['buckets'][key]
        ws2.cell(row=i, column=1, value=label)
        ws2.cell(row=i, column=2, value=b['count'])
        c = ws2.cell(row=i, column=3, value=round(float(b['total'])))
        c.number_format = money_fmt

    detail_header = 7
    headers2 = ['Proyecto', 'Cliente', 'Último cobro', 'Saldo', 'Antigüedad (días)']
    for col, title in enumerate(headers2, start=1):
        cell = ws2.cell(row=detail_header, column=col, value=title)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center')
    for i, row in enumerate(receivables['rows'], start=detail_header + 1):
        project = row['project']
        client = row['client']
        ws2.cell(row=i, column=1, value=f"#{project.pk} {project.type}")
        ws2.cell(row=i, column=2, value=(client.name if client else '—'))
        ws2.cell(row=i, column=3, value=(row['last_payment_date'].strftime('%d/%m/%Y')
                                         if row['last_payment_date'] else 'Nunca'))
        c = ws2.cell(row=i, column=4, value=round(float(row['saldo'])))
        c.number_format = money_fmt
        ws2.cell(row=i, column=5, value=row['days'])
    for col, w in enumerate((22, 22, 16, 16, 18), start=1):
        ws2.column_dimensions[chr(64 + col)].width = w

    return _xlsx_response(wb, "agrimit_movimientos.xlsx")


@login_required
def export_balance_pdf(request: HttpRequest) -> HttpResponse:
    """Resumen anual imprimible (§7.4, fallback window.print()). GET ?year=Y."""
    now = datetime.now()
    try:
        year = int(request.GET.get('year', now.year))
    except (TypeError, ValueError):
        year = now.year

    monthly_totals, year_total = balance_anual(year, request.user)
    kpis = get_balance_kpis(request.user, year, now.month if year == now.year else 12)
    return render(request, 'accounting/balance_print.html', {
        'year': year,
        'monthly_totals': monthly_totals,
        'neto_anual': year_total,
        'kpis': kpis,
    })