
from django.db import DatabaseError, transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
import logging
logger = logging.getLogger(__name__)
from apps.clients.models import Client
from apps.project_admin.models import Event, Project
from apps.accounting.views import create_account
from apps.project_admin.forms import ProjectForm
from django.contrib.auth.decorators import login_required

from .forms import ClientForm

def save_client_history(client_pk: int = None, event_type: str = "", msg: str = "", user=None):
    """Save a client-related event in the history"""
    try:
      
        # Create Event instance step by step to isolate the issue
        event = Event()
       
        
        event.user = user
        
        
        event.client_pk = client_pk
      
        
        event.type = event_type
      
        
        event.msg = msg
       
        
        event.save()
       
        
    except Exception as e:
        logger.error(f"Cannot save client history: {str(e)}")
        logger.error(f"Error details - client_pk={client_pk}, event_type={event_type}, msg={msg}, user={user}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise  # Re-raise the exception to see the full traceback

# Import the project history function
from apps.project_admin.views import save_in_history as save_project_history



#Creacion de cliente
@login_required
@transaction.atomic
def create_client_view(request: HttpRequest) -> HttpResponse:
    
    if request.method == 'POST':
        if request.POST.get('name') != '':
            try:
                
                client = Client.objects.create(
                    user=request.user, 
                    name=request.POST.get('name'), 
                    phone=request.POST.get('phone', ''), 
                    email=request.POST.get('email', ''), 
                    id_type=request.POST.get('id_type', 'DNI'),
                    id_number=request.POST.get('id_number', ''),
                    flag=True
                )
                # No need to call client.save() after create()
                
                msg = f"Se ha creado un nuevo cliente: {client.name}"
            
                
                # Debug: ensure parameters are correct types
                client_pk_value = client.pk
                user_value = request.user
            
                
                save_client_history(
                    client_pk=client_pk_value, 
                    event_type='newc', 
                    msg=msg, 
                    user=user_value
                )
                logger.info("Client history saved successfully")
                return redirect('clients')
            except Exception as e:
                logger.error(f"Error creating client create_cliente_v: {str(e)}")
                return render(request, 'clients/create_client_template.html', {'error': 'Error creating client.'})
    form = ClientForm()
    return render (request, 'clients/create_client_template.html', {'form': form})

#Vista de clientes
@login_required
@transaction.atomic
def clients_view(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        try:
            if request.POST.get('client-name') != '':
                client = Client.objects.create(
                    user=request.user, 
                    name=request.POST.get('client-name'), 
                    phone=request.POST.get('client-phone', ''), 
                    email=request.POST.get('client-email', ''),
                    id_type=request.POST.get('client-id_type', 'DNI'),
                    id_number=request.POST.get('client-id_number', '0'),
                    flag=True  # Set flag=True for new clients
                )
                # No need to call client.save() after create()
                msg = f"Se ha creado un nuevo cliente: {client.name}"
                save_client_history(client.pk, 'newc', msg, request.user)
            return redirect('clients')
        except Exception as e:
            logger.error(f"Error creating client clientsview: {str(e)}")
            return render(request, 'clients/clients_template.html', {'error': 'Error creating client.'}) 
    else:
        try:
            clients = Client.objects.filter(user=request.user).only('id', 'name', 'phone').order_by('name')

            context = {'clients': clients}
            return render (request, 'clients/clients_template.html', context)
        except DatabaseError as e:
            logger.error(f"Database error while fetching clients: {str(e)}")
            return render(request, 'clients/clients_template.html', {'error': 'Error fetching clients.'})
    return render (request, 'clients/clients_template.html', {'clients':clients})

#Creacion de proyecto a partir de un cliente
@login_required
@transaction.atomic
def create_for_client(request: HttpRequest, pk: int) -> HttpResponse:
    try:
        # Ensure the client belongs to the current user
        client = Client.objects.get(pk=pk, user=request.user)
    except Client.DoesNotExist:
        logger.error(f"User {request.user.id} tried to access client {pk} which doesn't exist or doesn't belong to them")
        return render(request, 'clients/project_for_client.html', {'error': 'Client not found or access denied.'})
    if request.method == 'POST':
        form = ProjectForm(request.POST)    
        if form.is_valid():
            try:
                form_instance = form.save(commit=False)
                form_instance.client = client
                form_instance.user = request.user  # Set the user who is creating the project
                form_instance.save()#Se guarda la instancia 
                msg = "Se ha creado un nuevo proyecto"   
                save_project_history(form_instance.pk, 'newp', msg, request.user)
                create_account(form_instance.pk)
                if 'save_and_backhome' in request.POST:
                    return redirect('projects')
            except Exception as e:
                logger.error(f"Error creating project for client {pk}: {str(e)}")
                return render(request, 'clients/project_for_client.html', {'error': 'Error creating project.'})    
        else:
            # Form data is not valid, handle the errors
            errors = form.errors.as_data()
            for field, error_list in errors.items():
                for error in error_list:
                    # Access the error message for each field
                    error_message = error.message
                    print(f"Error for field '{field}': {error_message}")    
    form = ProjectForm()
    return render (request, 'clients/project_for_client.html', {'form':form})

#Remover un cliente de la lista de clientes en formulario de creacion
@login_required
def clientedislist(request: HttpRequest, pk: int) -> HttpResponse:
    client = Client.objects.get(pk=pk)
    client.not_listed = True
    client.save()
    return redirect('clients')

def deleteclient(request: HttpRequest, pk: int) -> HttpResponse:
    try:
        client = Client.objects.get(pk=pk, user=request.user)
        msg = f"Cliente {client.name} eliminado"
        client.delete()
        save_client_history(pk, 'deletec', msg, request.user)
        return redirect('clients')
    except Client.DoesNotExist:
        logger.error(f"User {request.user.id} tried to delete client {pk} which doesn't exist or doesn't belong to them")
        return render(request, 'clients/clients_template.html', {'error': 'Client not found or access denied.'})
