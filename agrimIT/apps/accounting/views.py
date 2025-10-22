from datetime import datetime, timedelta
from decimal import Decimal
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

def create_acc_entry(project: Project, 
                     field: str, 
                     old_value: Optional[Decimal] = None, 
                     new_value: Optional[Decimal] = None,
                     msg: Optional[str] = None,
                     ) -> Optional[Account]:
    """
    Create an account entry for a project when a field is updated.
     Args:
        project_id: The ID of the project.
        field: The field being updated ('adv', 'exp', or 'est').
        old_value: The previous value.
        new_value: The new value.
        msg: Optional message for the movement description.
        
    Returns:
        The updated account object, or None if the operation failed.
    """
    # Ensure we're working with Decimal objects to avoid type errors
    if old_value is None:
        old_value = Decimal('0.00')
    elif not isinstance(old_value, Decimal):
        try:
            old_value = Decimal(str(old_value))
        except:
            old_value = Decimal('0.00')
            
    if new_value is None:
        new_value = Decimal('0.00')
    elif not isinstance(new_value, Decimal):
        try:
            new_value = Decimal(str(new_value))
        except:
            new_value = Decimal('0.00')

    logger.debug(f"Processing: project_id={project.id}, field={field}, old_value={old_value}, new_value={new_value}")

    try:
        with transaction.atomic():
            # Get project
            project = get_object_or_404(Project, id=project.id)
            logger.debug(f"Found project: {project}")
            
            # Get or create account using the helper function
            account, created = get_or_create_account(project)
            logger.info(f"{'Created new' if created else 'Using existing'} account for project {project.id}")
            
            # Get or create the monthly summary
            current_year = int(timezone.now().year)
            current_month = int(timezone.now().month)
            
            monthly_summary, createdm = MonthlyFinancialSummary.objects.get_or_create(
                user=project.user,
                year=current_year,
                month=current_month,
                defaults={
                    'total_advance': Decimal('0.00'),
                    'total_expenses': Decimal('0.00'),
                    'income_mensura': Decimal('0.00'),
                    'income_est_parc': Decimal('0.00'),
                    'income_leg': Decimal('0.00'),
                    'income_amoj': Decimal('0.00'),
                    'income_relev': Decimal('0.00'),
                }
            )
            
            if createdm:
                logger.info(f"Monthly summary created for {current_year}-{current_month}")
            else:
                logger.debug(f"Using existing monthly summary for {current_year}-{current_month}")
            
            # Process based on field type
            if field == 'adv':
                if created:
                    # For new accounts, set the initial value directly
                    Account.objects.filter(id=account.id).update(advance=new_value)
                else:
                    # For existing accounts, add to current value
                    Account.objects.filter(id=account.id).update(advance=F('advance') + new_value)
                
                if createdm:
                    # For new monthly summaries, set the initial value directly
                    MonthlyFinancialSummary.objects.filter(id=monthly_summary.id).update(total_advance=new_value)
                else:
                    # For existing summaries, add to current value
                    MonthlyFinancialSummary.objects.filter(id=monthly_summary.id).update(total_advance=F('total_advance') + new_value)
                
                define_type_for_summary(monthly_summary, project.type, new_value)
                if new_value < 0:
                    acc_mov_description = f"Se devolvieron ${abs(new_value)}"
                else:
                    acc_mov_description = f"Se cobraron ${new_value}"
                    
            elif field == 'exp':
                logger.debug(f"Monthly expenses before update: {monthly_summary.total_expenses}")
                
                if created:
                    # For new accounts, set the initial value directly
                    Account.objects.filter(id=account.id).update(expense=new_value)
                else:
                    # For existing accounts, add to current value
                    Account.objects.filter(id=account.id).update(expense=F('expense') + new_value)

                if createdm:
                    # For new monthly summaries, set the initial value directly
                    MonthlyFinancialSummary.objects.filter(id=monthly_summary.id).update(total_expenses=new_value)
                else:
                    # For existing summaries, add to current value
                    MonthlyFinancialSummary.objects.filter(id=monthly_summary.id).update(total_expenses=F('total_expenses') + new_value)
                
                define_type_for_summary(monthly_summary, project.type, -new_value)
                if new_value < 0:
                    acc_mov_description = f"Se redujo el gasto en ${abs(new_value)}"
                else:
                    acc_mov_description = f"Se ingreso el gasto de ${new_value}"  
                    
                # Refresh to see actual values after update
                monthly_summary.refresh_from_db()
                logger.debug(f"Monthly expenses after update: {monthly_summary.total_expenses}") 
                
            elif field == 'est':
                Account.objects.filter(id=account.id).update(estimated=new_value)
                acc_mov_description = f"Se ingreso costo final de ${new_value}"
            else:
                logger.error(f"Invalid field type '{field}'")
                return None
            
    
            
            

            # No need to save explicitly since we're using .update() which saves to DB directly
            # The .update() calls above already persisted the changes to the database
            
            # Use custom message if provided, otherwise use default description
            description = msg if msg is not None else acc_mov_description
            
            # Create movement record
            movement = AccountMovement.objects.create(
                user = project.user,
                account=account,
                
                amount=new_value,
                movement_type='ADV' if field == 'adv' else 'EXP' if field == 'exp' else 'EST',
                description=description
            )
            logger.info(f"Created movement record: {movement}")
            
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
    if request.method == 'POST':
        project = get_object_or_404(Project, id=pk)
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

    return render(request, 'accounting/account_form.html', {'form': form})

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
    
    return render(request, 'accounting/accounting_history.html', context)

def define_type_for_summary(summary: MonthlyFinancialSummary, 
                            project_type: str, 
                            amount: Decimal
                            ) -> None:
    """
    Helper function to define the project type and update the summary using F() expressions.
    This ensures atomic database updates and prevents race conditions.
    """
    summary_id = summary.id
    
    if project_type == 'Mensura':
        MonthlyFinancialSummary.objects.filter(id=summary_id).update(
            income_mensura=F('income_mensura') + amount
        )
      
    elif project_type == 'Estado Parcelario':
        MonthlyFinancialSummary.objects.filter(id=summary_id).update(
            income_est_parc=F('income_est_parc') + amount
        )
    elif project_type == 'Amojonamiento':
        MonthlyFinancialSummary.objects.filter(id=summary_id).update(
            income_amoj=F('income_amoj') + amount
        )
    elif project_type == 'Relevamiento':
        MonthlyFinancialSummary.objects.filter(id=summary_id).update(
            income_relev=F('income_relev') + amount
        )
    elif project_type == 'Legajo Parcelario':
        MonthlyFinancialSummary.objects.filter(id=summary_id).update(
            income_leg=F('income_leg') + amount
        )
    else:
        logger.error(f"Unknown project type: {project_type}. Cannot update summary.")



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
                'total_networth': format_currency(summary.net_worth),
                'project_count': project_counts.get(month_num, 0)
            })
            year_networth += summary.net_worth
        else:
            # If no summary exists for this month, create a default one
            monthly_totals.append({
                'month': month_name,
                'total_networth': format_currency(0),
                'project_count': project_counts.get(month_num, 0)
            })
    return monthly_totals, format_currency(year_networth)

#Balance
@login_required
def balance(request: HttpRequest) -> HttpResponse:
    method_post = False
    non_exist = False
    if request.method == 'POST':
        method_post = True
        #Aqui el user selecciona el mes y año
        date = request.POST.get('date')
        date_split = date.split("-")
        month = int(date_split[1])
        year = int(date_split[0])
       

    else:
        #Si no selecciona nada, se toma el mes y año actual
        month = datetime.now().month
        year = datetime.now().year
        #Obtengo los proyectos del mes y año actual, pero solo los que no estan cerrados
    try:
        balance_data = get_financial_data(year, month, request.user)
        data, year_total = balance_anual(year, request.user)
        if balance_data['objects']['monthly_summary'] is None:
            non_exist = True
            chart_data = None
        else:
            chart_data = chart_data_format(balance_data)
        
    except Exception as e:
        # Manejo de errores
        logger.error(f"Error al sdsaobtener datos financieros: {e}")
        non_exist = True
        

    return render (request, 'accounting/balance.html', {
        'method_post':method_post,
        'total':balance_data['formatted']['total'], 
        'adv':balance_data['formatted']['adv'], 
        'pending':balance_data['formatted']['pending'],
        'cant':balance_data['counts']['total'],
        'cant_actual_month':balance_data['counts']['current_month'],
        'cant_previus_months':balance_data['counts']['previous_months'],
        'gastos':balance_data['formatted']['exp'], 
        'net':balance_data['formatted']['net'],
        'month':month_str(month),
        'month_number': month,  # Pass the numeric month as well 
        'year':year,
        'monthly_totals': data,
        'neto_anual': year_total,
        'chart_data': chart_data,
        'non_exist': non_exist
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