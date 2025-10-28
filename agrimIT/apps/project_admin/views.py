import io
import time
from django.utils import timezone
from urllib.error import URLError
from urllib.request import urlopen
from django.http import FileResponse, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.core.paginator import Paginator, PageNotAnInteger
from django.db import DatabaseError, transaction
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import logging
logger = logging.getLogger(__name__)
from django.conf import settings
from apps.accounting.views import create_acc_entry, create_account, get_or_create_account
from apps.clients.models import Client
from apps.project_admin.forms import FileFieldForm, ProjectForm, ProjectFullForm
from apps.project_admin.models import Event, Project, ProjectFiles
from apps.accounting.models import Account, MonthlyFinancialSummary
from django.db.models import Q
from decimal import Decimal as Dec
from django.contrib.auth.decorators import login_required
from collections import defaultdict
from .supabase_client import supabase
import random
from datetime import datetime, timedelta

# Create your views here.
def paginate_queryset(request: HttpRequest, queryset, per_page=12) -> tuple: 
    """Paginate any queryset and handle pagination errors"""
    num_page = request.GET.get('page')
    paginator = Paginator(queryset, per_page)
    try:
        page_obj = paginator.get_page(num_page)
    except PageNotAnInteger:
        page_obj = paginator.get_page(1)
    return page_obj, paginator

#Registro en historial
def save_in_history(project_pk: int, event_type: str, msg: str, user=None):
    """Save an event in the project history"""
    try:
        # Try to get the project first
        project = Project.objects.get(pk=project_pk)
        Event.objects.create(
            project=project, 
            project_pk=project_pk,
            type=event_type,
            msg=msg,
            user=user or project.user  # Use provided user or fallback to project owner
        )
    except Project.DoesNotExist:
        # Project doesn't exist (probably deleted), create event without project reference
        Event.objects.create(
            project=None,  # No project reference since it's deleted
            project_pk=project_pk,  # Keep the PK for reference
            type=event_type,
            msg=msg,
            user=user  # Must provide user when project doesn't exist
        )
    except Exception as e:
        logger.error(f"Cannot save history: {e}")

@login_required
def index(request):
    projects = Project.objects.select_related('client')\
        .prefetch_related('files')\
        .filter(user=request.user).order_by('-created')[:10]
    clients_count = Client.objects.filter(user=request.user, flag=True).count()
    project_count = Project.objects.filter(user=request.user, closed=False).count()
    net_income = Dec("0.00")
    current_year = int(timezone.now().year)
    current_month = int(timezone.now().month)
    summary = MonthlyFinancialSummary.objects.filter(
        year=current_year, month=current_month, user=request.user
        ).first()
    net_income = summary.net_worth if summary else Dec("0.00")
    return render (request, 'base/Index.html', {'projects': projects, 'clients_count': clients_count, 'project_count': project_count, 'net_income': net_income})

#Eliminación de2 proyecto
@login_required
@transaction.atomic
def delete_view(request: HttpRequest, pk: int) -> HttpResponse:
    """ Delete a project and its associated files """
    try:
        if request.method == 'POST':
            project = Project.objects.select_related('client').filter(
                user=request.user  # Filter by current user
            ).get(pk=pk)
            msg = f"Se ha eliminado un proyecto {project.type} de {project.client.name}"
            
            # Handle file deletion inline
            file = ProjectFiles.objects.filter(project=project).first()
            if file:
                try:
                    bucket_name = settings.SUPABASE_BUCKET
                    supabase.storage.from_(bucket_name).remove([file.name])
                    file.delete()
                except Exception as e:
                    logger.error(f"Error deleting file for project {pk}: {str(e)}")
            
            # Delete the associated account if exists
            if project.account:
                try:
                    project.account.delete()
                except Exception as e:
                    logger.error(f"Error deleting account for project {pk}: {str(e)}")
            
            # Save history BEFORE deleting project
            save_in_history(pk, 'deletep', msg, request.user)
            
            # Finally delete the project
            project.delete()
        return redirect('index')
    except Project.DoesNotExist:
        logger.error(f"Project with pk {pk} does not exist for current user.")
        return redirect('index')

#Archivado de proyectos
@login_required
@transaction.atomic
def close_view(request: HttpRequest, pk: int) -> HttpResponse:
    """ Close a project by setting its closed field to True """
    try:
        project = Project.objects.filter(user=request.user).get(pk=pk)
        project.closed = True
        project.save()
        msg = "Se ha cerrado un proyecto"
        save_in_history(pk, 'modp', msg, request.user)
        return redirect('projects')
    except Project.DoesNotExist:
        logger.error(f"Project with pk {pk} does not exist for current user.")
        return redirect('projects')

#Todos los proyectos
@login_required
def projectlist_view(request: HttpRequest) -> HttpResponse:
    """ List all projects for the current user """
    if request.method == 'POST':
        if request.POST.get('search-input')!="":
            query = request.POST.get('search-input')
            projects = Project.objects.select_related('client')\
                .prefetch_related('files')\
                .filter(user=request.user)\
                .filter(Q(client__name__icontains=query) | Q(partida__icontains=query))\
                .order_by('-created')
            
            if not projects.exists():
                return render (request, 'project_admin/project_list_template.html', {'no_projects':True})
        actual_pag, pages = paginate_queryset(request, projects)
        return render (request, 'project_admin/project_list_template.html', {'projects':actual_pag, 'pages':pages})

    else:
        actual_pag, pages = paginate_queryset(request, 
            Project.objects.select_related('client')
            .prefetch_related('files', 'events')
            .filter(user=request.user, closed=False)
            .order_by('-created')
        )
    return render (request, 'project_admin/project_list_template.html', {'projects':actual_pag, 'pages':pages})

#Proyectos por cliente
@login_required
def alt_projectlist_view(request: HttpRequest, pk: int) -> HttpResponse:
    """ List projects for a specific client """
    projects = Project.objects.select_related('client')\
        .prefetch_related('files')\
        .filter(user=request.user, client__pk=pk).order_by('-created')
    if not projects.exists():
        return render (request, 'project_admin/project_list_template.html', {'no_projects':True})
    actual_pag, pages = paginate_queryset(request, projects)
    return render (request, 'project_admin/project_list_template.html', {'projects':actual_pag, 'pages':pages})

#Proyectos por tipo
@login_required
def projectlistfortype_view(request: HttpRequest, type: int) -> HttpResponse:
    """ List projects for a specific type """
    #Mensuras
    type_map = {
        1: "Mensura",
        2: "Estado Parcelario",
        3: "Amojonamiento",
        4: "Relevamiento",
        5: "Legajo Parcelario"
    }
    project_type = type_map.get(type)
    if not project_type:
        return render(request, 'project__admin/project_list_template.html', {'no_projects': True})
    projects = Project.objects.select_related('client')\
        .prefetch_related('files')\
        .filter(user=request.user, type=project_type, closed=False).order_by('-created')
    actual_pag, pages = paginate_queryset(request, projects)
    if not projects.exists():
        return render (request, 'project_admin/project_list_template.html', {'no_projects':True})
    return render (request, 'project_admin/project_list_template.html', {'projects':actual_pag, 'pages':pages})

#Vista de un proyecto
@login_required
def project_view(request: HttpRequest, pk: int) -> HttpResponse:
    """ View a specific project """
    try:
        project = Project.objects.select_related(
            'account','client', 'user'
        ).prefetch_related(
            'files'
        ).filter(user=request.user).get(pk=pk)
        #Security check
        if project.user != request.user:
            logger.warning(f"User {request.user} tried to access project {pk} that does not belong to them.")
            return redirect('projects')
        file = project.files.first()
        if file:
            return render(request, 'project_admin/project_template.html', {'project': project, 'account': project.account, 'file_url': file.url})
        else:
            form = FileFieldForm()
        return render(request, 'project_admin/project_template.html', {'project': project, 'account': project.account, 'form': form})
    except Project.DoesNotExist:
        logger.error(f"Project with ID {pk} does not exist for current user.")
        return redirect('projects')
    except Exception as e:
        logger.error(f"Unexpected error in project_view for project {pk}: {str(e)}")
        return render(request, 'project_admin/project_template.html', {
            'error': 'Error al cargar el proyecto. Intente nuevamente.',
            'project_id': pk
        })


#Vista formulario de creacion
@login_required
def create_view(request: HttpRequest) -> HttpResponse:
    """ Create a new project """
    if request.method == 'POST':
        logger.info("Project creation started", extra={
            'user_id': request.user.id,
            'form_data_keys': list(request.POST.keys())
        })
        
        form = ProjectForm(request.POST)    
        if form.is_valid():
            logger.info("Project form validation successful", extra={
                'user_id': request.user.id,
                'project_type': form.cleaned_data.get('type')
            })
            
            with transaction.atomic():
                form_instance = form.save(commit=False)
                # Associate the current user with the project
                form_instance.user = request.user
                
                client = None
                client_pk = request.POST.get('client-pk') or request.POST.get('client-list')
                if client_pk:
                    client = Client.objects.get(pk=client_pk)
                    logger.info("Existing client selected", extra={
                        'user_id': request.user.id,
                        'client_id': client_pk
                    })
                else:
                    client_name = request.POST.get('client-name')
                    client = Client.objects.filter(user=request.user, name=client_name).first()
                    if not client:
                        client = Client.objects.create(
                            name=client_name,
                            phone=request.POST.get('client-phone'),
                            user=request.user,
                            email=request.POST.get('client-email'),
                        )
                        logger.info("New client created", extra={
                            'user_id': request.user.id,
                            'client_name': client_name,
                            'client_id': client.id
                        })
                        
                form_instance.client = client
                form_instance.save()
                #Se guarda la instancia
                msg = "Se ha creado un nuevo proyecto"   
                pk = form_instance.pk
                
                logger.info("Project created successfully", extra={
                    'user_id': request.user.id,
                    'project_id': pk,
                    'project_type': form_instance.type,
                    'client_name': client.name
                })
                
                save_in_history(pk, 'newp', msg, request.user)
                create_account(pk)
                if 'save_and_backhome' in request.POST:
                    return redirect('projectview', pk=pk)
                
        else:
            # Form data is not valid, handle the errors
            logger.warning("Project form validation failed", extra={
                'user_id': request.user.id,
                'form_errors': dict(form.errors),
                'form_data': dict(request.POST)
            })
            
            errors = form.errors.as_data()
            for field, error_list in errors.items():
                for error in error_list:
                    # Access the error message for each field
                    error_message = error.message
                    
    logger.info("Project creation form requested", extra={
        'user_id': request.user.id,
        'method': request.method
    })
                    
    form = ProjectForm()
    clients = Client.objects.all().filter(flag=True).order_by('name')
    return render (request, 'project_admin/form.html', {'form':form, 'clients':clients})

#vista de modificacion
@login_required
@transaction.atomic
def mod_view(request: HttpRequest, pk: int) -> HttpResponse:
    """ Modify an existing project """
    if request.method == 'POST':
        try:
            project_instance = Project.objects.select_related('client').filter(user=request.user).get(pk=pk)
            msg = "" 
            if request.POST.get('contact_name'):
                project_instance.contact_name = request.POST.get('contact_name')
                project_instance.contact_phone = request.POST.get('contact_phone')        
            if request.POST.get('client-data') == '':
                project_instance.titular_name = project_instance.client.name
                project_instance.titular_phone = project_instance.client.phone
            if request.POST.get('titular'):
                project_instance.titular_name = request.POST.get('titular')
            if request.POST.get('titular_phone'):
                project_instance.titular_phone = request.POST.get('titular_phone')
            if request.POST.get('proc'):
                project_instance.procedure = request.POST.get('proc')
            if request.POST.get('insctype'):
                project_instance.inscription_type = request.POST.get('insctype')
            if request.POST.get('price'):
                try:
                    previous_price = project_instance.account.estimated
                    msg = f"Se establecio el presupuesto del proyecto {project_instance.pk}"
                    create_acc_entry(project_instance, 'est', previous_price, Dec(request.POST.get('price')))
                except:
                    project_instance.account.estimated = Dec("0,00")
            if request.POST.get('adv'):
                try:
                    newadv_asdecimal = Dec(request.POST.get('adv'))
                    previous_adv = project_instance.account.advance
                    if newadv_asdecimal < 0:
                        msg = f"Se devolvieron ${abs(newadv_asdecimal)} del proyecto {project_instance.pk}"
                    else:
                        msg = f"Se cobraron ${newadv_asdecimal} del proyecto {project_instance.pk}"
                    create_acc_entry(project_instance, 'adv', previous_adv, newadv_asdecimal)
                except:
                    project_instance.account.advance = Dec("0.00")
            if request.POST.get('gasto'):
                try:
                    newgasto_asdecimal = Dec(request.POST.get('gasto'))
                    previous_gasto = project_instance.account.expense
                    if newgasto_asdecimal < 0:
                        msg = f"Se redujo ${abs(newgasto_asdecimal)} el gasto del proyecto {project_instance.pk}"
                    else:
                        msg = f"Se debitaron ${newgasto_asdecimal} al proyecto {project_instance.pk}"
                    create_acc_entry(project_instance, 'exp', previous_gasto, newgasto_asdecimal)
                except:
                    project_instance.account.expense = Dec("0.00")


            project_instance.save()
            if msg == "":
                msg = "Se ha modificado un proyecto"
            pk = project_instance.pk
            save_in_history(pk, 'modp', msg, request.user)
            prev = request.META.get('HTTP_REFERER')
            return redirect(prev)
        except Project.DoesNotExist:
            logger.error(f"Project with pk {pk} does not exist for current user.")
            return render(request, 'project_admin/project_template.html', {'error': 'Project not found.'})
        except Exception as e:
            logger.error(f"Error updating: {str(e)}")
            return render(request, 'project_admin/project_template.html', {'error': 'Error saving project.'})

    prev = request.META.get('HTTP_REFERER')
    return redirect(prev)

#Modificacion total del proyecto
@login_required
@transaction.atomic
def full_mod_view(request: HttpRequest, pk: int) -> HttpResponse:
    """ Modify all fields of an existing project """
    if request.method == 'POST':
        instance = Project.objects.filter(user=request.user).get(pk=pk)
        form = ProjectFullForm(request.POST, instance=instance)
        
        if form.is_valid():
            try:
                form.save()
                msg = "Se ha modificado un proyecto"   
                save_in_history(instance.pk, 'modp', msg, request.user)
                return redirect('projectview', pk=pk)
            except Exception as e:
                logger.error(f"Error saving full project modification: {str(e)}")
                return render(request, 'project_admin/full_mod_template.html', {'error': 'Error saving project.'})
    else:
        instance = Project.objects.filter(user=request.user).get(pk=pk)
        form = ProjectFullForm(instance=instance)
    return render (request, 'project_admin/full_mod_template.html', {'form':form, 'project':instance})

#Vista de historial
@login_required
def history_view(request: HttpRequest) -> HttpResponse:
    """ View the history of events for the current user """
    events = Event.objects.filter(user=request.user).order_by('-time')[:100]
    if not events:
        return render (request, 'project_admin/history_template.html', {'no_events':True})
    grouped_objects_def = defaultdict(lambda: defaultdict(list))
    for e in events:
        
        if e.type == 'deletep' or e.type == 'deletec':
            e.link = False
        else:
            e.link = True
        year = e.time.year
        month = e.time.month
        grouped_objects_def[year][month].append(e)

    for obj in grouped_objects_def:
       grouped_objects_def[obj].default_factory = None
    grouped_objects = dict(grouped_objects_def)
    return render (request, 'project_admin/history_template.html', {'yearlist':grouped_objects})

#Modulo de busqueda
@login_required
def search(request: HttpRequest) -> JsonResponse:
    """ Search for projects based on a query string - OPTIMIZED """
    try:
        query = request.GET.get('query', '').strip()  # Get and clean the search query
        
        # Validate query length to prevent expensive searches
        if not query or len(query) < 2:
            return JsonResponse({'results': []}, safe=False)
        
        # Perform your search logic here and get the results
        if query:
            # Optimized search query with multiple search fields
            search_filter = Q(client__name__icontains=query) | \
                          Q(partida__icontains=query) | \
                          Q(titular_name__icontains=query) | \
                          Q(type__icontains=query)
            
            objectc = Project.objects.select_related('client')\
                .filter(user=request.user)\
                .filter(search_filter)\
                .only('id', 'type', 'created', 'titular_name', 'partida', 'client__name', 'closed')\
                .order_by('-created')[:5]
            
            # Use list comprehension for better performance
            results = [
                {
                    'id': obj.pk,
                    'type': obj.type,
                    'datecreated': obj.created.strftime('%d/%m/%Y'),
                    'client_name': obj.client.name if obj.client else 'Sin cliente',
                    'titular_name': obj.titular_name,
                    'partida': obj.partida,
                    'closed': obj.closed
                }
                for obj in objectc
            ]
        else:
            results = []
    
        return JsonResponse({
            'results': results,
            'query': query,
            'count': len(results)
        }, safe=False)
        
    except DatabaseError as e:
        # Log the database error
        logger.error(f"Database error in search view: {str(e)}", extra={
            'user_id': request.user.id,
            'query': query,
            'error_type': 'DatabaseError'
        })
        return JsonResponse({'error': 'Database error occurred.'}, status=500)
        
    except Exception as e:
        # Log unexpected errors
        logger.error(f"Unexpected error in search view: {str(e)}", extra={
            'user_id': request.user.id,
            'query': query,
            'error_type': type(e).__name__
        })
        return JsonResponse({'error': 'An error occurred while searching.'}, status=500)

#Modulo descargas
@login_required
def download_file(request: HttpRequest, pk: int) -> HttpResponse:
    """ Download a file associated with a project """
    try:
        # First verify the project belongs to the current user
        project = Project.objects.filter(user=request.user).get(pk=pk)
        file = ProjectFiles.objects.get(project=project)
        file_name = file.name
        bucket_name = settings.SUPABASE_BUCKET
        
        file_url = supabase.storage.from_(bucket_name).get_public_url(file_name)
        response = urlopen(file_url)
        file_content = io.BytesIO(response.read())
        return FileResponse(file_content, as_attachment=True, filename=file_name)
    except Project.DoesNotExist:
        logger.error(f"Project with pk {pk} does not exist for current user.")
        return JsonResponse({'error': 'Project not found'}, status=404)
    except ProjectFiles.DoesNotExist:
        logger.error(f"No file found for project {pk}.")
        return JsonResponse({'error': 'File not found'}, status=404)
    except URLError as e:
        logger.error(f"Error downloading file: {str(e)}")
        return JsonResponse({'error': 'Failed to download file'}, status=500)

#Modulo de subida de archivos
@login_required
@transaction.atomic
def upload_files(request: HttpRequest, pk: int) -> HttpResponse:
    if request.method == 'POST':
        logger.info("File upload started", extra={
            'user_id': request.user.id,
            'project_id': pk
        })
        
        form = FileFieldForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                file = request.FILES['file_field']
                timestamp = int(time.time())
                file_name = f"{pk}_{timestamp}_{file.name}"
                file_size = file.size
                
                logger.info("File upload processing", extra={
                    'user_id': request.user.id,
                    'project_id': pk,
                    'original_filename': file.name,
                    'file_size': file_size,
                    'processed_filename': file_name
                })
                
                bucket_name = settings.SUPABASE_BUCKET
                file.seek(0)  # Reset file pointer to beginning
                file_content = file.read()  # Read as bytes
                supabase.storage.from_(bucket_name).upload(file_name, file_content)
                file_url = supabase.storage.from_(bucket_name).get_public_url(file_name)
                ProjectFiles.objects.create(project=Project.objects.get(pk=pk), name=file_name, url=file_url)
                save_in_history(pk, 'file_add', f"Se subió el archivo {file_name}", request.user)
                
                logger.info("File upload successful", extra={
                    'user_id': request.user.id,
                    'project_id': pk,
                    'filename': file_name,
                    'file_size': file_size
                })
                
            except Exception as e:
                logger.error("File upload failed", extra={
                    'user_id': request.user.id,
                    'project_id': pk,
                    'error': str(e),
                    'filename': file.name if 'file' in locals() else 'unknown'
                })
        else:
            logger.warning("File upload form validation failed", extra={
                'user_id': request.user.id,
                'project_id': pk,
                'form_errors': dict(form.errors)
            })
                
    prev = request.META.get('HTTP_REFERER')
    return redirect(prev)

#Modulo de eliminacion de archivos
@login_required
@transaction.atomic
def delete_file(request: HttpRequest, pk: int) -> HttpResponse:
    """ Delete a file associated with a project """
    try:
        # First verify the project belongs to the current user
        project = Project.objects.filter(user=request.user).get(pk=pk)
        file = ProjectFiles.objects.get(project=project)
        bucket_name = settings.SUPABASE_BUCKET
        supabase.storage.from_(bucket_name).remove([file.name])
        file_name = file.name
        file.delete()
        
        # Save event in history
        save_in_history(pk, 'file_del', f"Se eliminó el archivo {file_name}", request.user)
        
        prev = request.META.get('HTTP_REFERER')
        return redirect(prev)
    except Project.DoesNotExist:
        logger.error(f"Project with pk {pk} does not exist for current user.")
    except ProjectFiles.DoesNotExist:
        logger.error(f"No file found for project {pk}.")
    except Exception as e:
        logger.error(f"Error deleting file for project {pk}: {str(e)}")
        
    prev = request.META.get('HTTP_REFERER')
    return redirect(prev)
        
#Modulo de vista de archivos
@login_required
def file_view(request: HttpRequest, pk: int) -> HttpResponse:
    """ View files associated with a project """
    try:
        # First verify the project belongs to the current user
        project = Project.objects.filter(user=request.user).get(pk=pk)
        files = ProjectFiles.objects.filter(project=project)
        return render(request, 'project_admin/files_template.html', {'files': files})
    except Project.DoesNotExist:
        logger.error(f"Project with pk {pk} does not exist for current user.")
        return redirect('projects')

# Test data generation function
@login_required
@transaction.atomic
def generate_test_data(request: HttpRequest) -> HttpResponse:
    """
    Generate test projects with accounting data for each month of the current year.
    Creates 2 projects per month with realistic financial data.
    """
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Only superusers can generate test data'}, status=403)
    
    try:
        current_year = timezone.now().year
        project_types = ['Mensura', 'Estado Parcelario', 'Amojonamiento', 'Relevamiento', 'Legajo Parcelario']
        
        # Base client names for variety
        client_names = [
            'Juan Pérez', 'María González', 'Carlos Rodriguez', 'Ana Martín', 
            'Luis García', 'Carmen López', 'Miguel Fernández', 'Laura Sánchez',
            'José Díaz', 'Elena Ruiz', 'Francisco Torres', 'Pilar Moreno'
        ]
        
        created_projects = []
        
        for month in range(1, 13):  # Months 1-12
            for project_num in range(1, 3):  # 2 projects per month
                # Create a test client
                client_name = f"{random.choice(client_names)} {month:02d}-{project_num}"
                client = Client.objects.create(
                    user=request.user,
                    name=client_name,
                    phone=f"11-{random.randint(1000, 9999)}-{random.randint(1000, 9999)}",
                    email=f"test{month:02d}{project_num}@example.com",
                    flag=True
                )
                
                # Create project with realistic data
                project_type = random.choice(project_types)
                chacra_num = str(random.randint(1, 100)) if random.choice([True, False]) else ""
                quinta_num = str(random.randint(1, 100)) if not chacra_num else ""
                
                project = Project.objects.create(
                    user=request.user,
                    client=client,
                    type=project_type,
                    titular_name=client_name,
                    titular_phone=client.phone,
                    partido=f"Partido {random.randint(100, 999)}",
                    partida=f"{random.randint(10000, 99999)}",
                    circ=f"{random.randint(1, 20)}",
                    sect=f"{random.randint(1, 50)}",
                    chacra_num=chacra_num,
                    quinta_num=quinta_num,
                    parcela_num=str(random.randint(1, 999)),
                    street=f"Calle {random.choice(['San Martín', 'Belgrano', 'Rivadavia', 'Mitre'])}",
                    street_num=str(random.randint(100, 9999)),
                    inscription_type=random.choice(['Folio', 'Matricula']),
                    process_num=random.randint(10000, 99999),
                    procedure=f"Procedimiento {project_type}",
                    closed=random.choice([True, False]) if month < timezone.now().month else False
                )
                
                # Create account for the project
                account, created = get_or_create_account(project)
                
                # Generate realistic financial data
                base_budget = random.randint(50000, 500000)  # Between $50k and $500k
                budget = Dec(str(base_budget))
                
                # Advance payment (usually 30-70% of budget)
                advance_percentage = random.uniform(0.3, 0.7)
                advance = Dec(str(int(base_budget * advance_percentage)))
                
                # Expenses (usually 20-40% of budget)
                expense_percentage = random.uniform(0.2, 0.4)
                expenses = Dec(str(int(base_budget * expense_percentage)))
                
                # Update account with financial data
                account.estimated = budget
                account.advance = advance
                account.expense = expenses
                account.save()
                
                # Create accounting movements with backdated timestamps
                target_date = timezone.make_aware(datetime(current_year, month, random.randint(1, 28)))
                
                # Budget entry
                create_acc_entry(project, 'est', Dec('0'), budget)
                
                # Advance payment entry
                create_acc_entry(project, 'adv', Dec('0'), advance)
                
                # Expense entries (split into 2-3 transactions)
                remaining_expenses = expenses
                expense_count = random.randint(2, 3)
                for i in range(expense_count):
                    if i == expense_count - 1:  # Last expense gets the remainder
                        expense_amount = remaining_expenses
                    else:
                        expense_amount = Dec(str(int(float(remaining_expenses) * random.uniform(0.3, 0.6))))
                    
                    if expense_amount > 0:
                        create_acc_entry(project, 'exp', Dec('0'), expense_amount)
                        remaining_expenses -= expense_amount
                
                # Create history entries
                save_in_history(project.pk, 'newp', f"Proyecto de prueba creado - {project_type}", request.user)
                
                # Manually update created timestamp to spread across the year
                project.created = target_date
                project.save()
                
                created_projects.append({
                    'id': project.pk,
                    'type': project_type,
                    'client': client_name,
                    'month': month,
                    'budget': float(budget),
                    'advance': float(advance),
                    'expenses': float(expenses),
                    'net_worth': float(advance - expenses)
                })
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully created {len(created_projects)} test projects',
            'projects': created_projects,
            'summary': f'Created 2 projects for each month of {current_year}'
        })
        
    except Exception as e:
        logger.error(f"Error generating test data: {str(e)}")
        return JsonResponse({'error': f'Error generating test data: {str(e)}'}, status=500)

@login_required
@transaction.atomic
def generate_monthly_summaries(request: HttpRequest) -> HttpResponse:
    """
    Generate monthly financial summaries by collecting all accounting data 
    and calculating totals per month for the current user.
    """
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Only superusers can generate monthly summaries'}, status=403)
    
    try:
        from django.db.models import Sum, Q
        from apps.accounting.models import Account, AccountMovement
        
        # Get all projects for the user with their accounts
        user_projects = Project.objects.select_related('account', 'client')\
            .prefetch_related('account__movements')\
            .filter(
                user=request.user,
                account__isnull=False
            )
        
        # Dictionary to store monthly data
        monthly_data = {}
        created_summaries = []
        
        # Process each project
        for project in user_projects:
            created_date = project.created
            year = created_date.year
            month = created_date.month
            
            # Initialize month data if not exists
            month_key = f"{year}-{month:02d}"
            if month_key not in monthly_data:
                monthly_data[month_key] = {
                    'year': year,
                    'month': month,
                    'total_advance': Dec('0.00'),
                    'total_expenses': Dec('0.00'),
                    'income_mensura': Dec('0.00'),
                    'income_est_parc': Dec('0.00'),
                    'income_leg': Dec('0.00'),
                    'income_amoj': Dec('0.00'),
                    'income_relev': Dec('0.00'),
                }
            
            # Add project's financial data to monthly totals
            account = project.account
            
            # Skip if project doesn't have an account
            if not account:
                logger.warning(f"Project {project.pk} doesn't have an account, skipping financial data")
                continue
            
            monthly_data[month_key]['total_advance'] += account.advance
            monthly_data[month_key]['total_expenses'] += account.expense
            
            # Calculate net income for this project and add to appropriate category
            net_income = account.advance - account.expense
            
            # Categorize by project type
            project_type = project.type.lower()
            if 'mensura' in project_type:
                monthly_data[month_key]['income_mensura'] += net_income
            elif 'estado parcelario' in project_type or 'parcelario' in project_type:
                monthly_data[month_key]['income_est_parc'] += net_income
            elif 'legajo' in project_type:
                monthly_data[month_key]['income_leg'] += net_income
            elif 'amojonamiento' in project_type:
                monthly_data[month_key]['income_amoj'] += net_income
            elif 'relevamiento' in project_type:
                monthly_data[month_key]['income_relev'] += net_income
        
        # Create or update MonthlyFinancialSummary records
        for month_key, data in monthly_data.items():
            summary, created = MonthlyFinancialSummary.objects.update_or_create(
                user=request.user,
                year=data['year'],
                month=data['month'],
                defaults={
                    'total_advance': data['total_advance'],
                    'total_expenses': data['total_expenses'],
                    'income_mensura': data['income_mensura'],
                    'income_est_parc': data['income_est_parc'],
                    'income_leg': data['income_leg'],
                    'income_amoj': data['income_amoj'],
                    'income_relev': data['income_relev'],
                }
            )
            
            created_summaries.append({
                'month': data['month'],
                'year': data['year'],
                'total_advance': float(data['total_advance']),
                'total_expenses': float(data['total_expenses']),
                'net_worth': float(data['total_advance'] - data['total_expenses']),
                'created': created
            })
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully processed {len(created_summaries)} monthly summaries',
            'summaries': created_summaries,
            'total_projects_processed': len(user_projects)
        })
        
    except Exception as e:
        logger.error(f"Error generating monthly summaries: {str(e)}")
        return JsonResponse({'error': f'Error generating monthly summaries: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def log_frontend_error(request: HttpRequest) -> JsonResponse:
    """
    Log frontend JavaScript errors to Django logging system.
    This replaces console.log for critical error tracking.
    """
    try:
        data = json.loads(request.body)
        
        # Log the frontend error with context
        logger.error("Frontend JavaScript error", extra={
            'user_id': request.user.id if request.user.is_authenticated else 'anonymous',
            'error_message': data.get('message', 'No message'),
            'filename': data.get('filename', 'unknown'),
            'line_number': data.get('lineno', 'unknown'),
            'url': data.get('url', request.META.get('HTTP_REFERER', 'unknown')),
            'user_agent': request.META.get('HTTP_USER_AGENT', 'unknown'),
            'timestamp': timezone.now().isoformat()
        })
        
        return JsonResponse({'status': 'logged'})
    except Exception as e:
        logger.error(f"Error logging frontend error: {str(e)}")
        return JsonResponse({'error': 'Failed to log error'}, status=500)
