"""
Base views for AgrimIT project using Class-Based Views.
This file establishes patterns and conventions for all new views.
"""

from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView
)
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect
from apps.utils.mixins import (
    AgrimITBaseView, AjaxResponseMixin, MessageMixin, 
    SearchMixin, FilterMixin, TransactionMixin
)
import logging

logger = logging.getLogger(__name__)


class AgrimITListView(AgrimITBaseView, SearchMixin, FilterMixin, ListView):
    """
    Base list view for AgrimIT models.
    Includes automatic user filtering, search, and pagination.
    """
    paginate_by = 12
    template_name_suffix = '_list'
    context_object_name = 'objects'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_count'] = self.get_queryset().count()
        return context


class AgrimITDetailView(AgrimITBaseView, DetailView):
    """
    Base detail view for AgrimIT models.
    Automatically filters by user ownership.
    """
    template_name_suffix = '_detail'
    
    def get_object(self, queryset=None):
        """Override to add security logging"""
        obj = super().get_object(queryset)
        logger.info(f"User {self.request.user.id} accessed {obj.__class__.__name__} {obj.pk}")
        return obj


class AgrimITCreateView(AgrimITBaseView, MessageMixin, TransactionMixin, CreateView):
    """
    Base create view for AgrimIT models.
    Automatically assigns current user and shows success messages.
    """
    template_name_suffix = '_form'
    success_message = "Objeto creado exitosamente."
    
    def get_success_url(self):
        """Try to get success_url from multiple sources"""
        if hasattr(self, 'success_url') and self.success_url:
            return self.success_url
        if hasattr(self.object, 'get_absolute_url'):
            return self.object.get_absolute_url()
        return reverse_lazy('index')


class AgrimITUpdateView(AgrimITBaseView, MessageMixin, TransactionMixin, UpdateView):
    """
    Base update view for AgrimIT models.
    Automatically filters by user ownership and shows success messages.
    """
    template_name_suffix = '_form'
    success_message = "Objeto actualizado exitosamente."
    
    def get_success_url(self):
        """Try to get success_url from multiple sources"""
        if hasattr(self, 'success_url') and self.success_url:
            return self.success_url
        if hasattr(self.object, 'get_absolute_url'):
            return self.object.get_absolute_url()
        return reverse_lazy('index')


class AgrimITDeleteView(AgrimITBaseView, MessageMixin, DeleteView):
    """
    Base delete view for AgrimIT models.
    Automatically filters by user ownership and shows success messages.
    """
    template_name_suffix = '_confirm_delete'
    success_message = "Objeto eliminado exitosamente."
    
    def delete(self, request, *args, **kwargs):
        """Add logging and custom logic before deletion"""
        obj = self.get_object()
        logger.info(f"User {request.user.id} deleted {obj.__class__.__name__} {obj.pk}")
        
        response = super().delete(request, *args, **kwargs)
        
        if self.success_message:
            messages.success(request, self.success_message)
        
        return response


class AgrimITAjaxView(AgrimITBaseView, AjaxResponseMixin):
    """
    Base view for AJAX endpoints.
    Handles JSON responses and error handling.
    """
    
    def ajax_response(self, request, *args, **kwargs):
        """Override this method in subclasses"""
        try:
            data = self.get_ajax_data()
            return JsonResponse({'success': True, 'data': data})
        except Exception as e:
            logger.error(f"AJAX error in {self.__class__.__name__}: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    def get_ajax_data(self):
        """Override this method to return AJAX data"""
        raise NotImplementedError("Subclasses must implement get_ajax_data()")


# Example usage patterns for future views:

"""
# Project List View Example:
class ProjectListView(AgrimITListView):
    model = Project
    search_fields = ['client__name', 'partida', 'titular_name']
    filter_fields = {'type': 'type', 'closed': 'closed'}
    template_name = 'project_admin/project_list.html'
    context_object_name = 'projects'

# Project Detail View Example:
class ProjectDetailView(AgrimITDetailView):
    model = Project
    template_name = 'project_admin/project_detail.html'
    context_object_name = 'project'

# Project Create View Example:
class ProjectCreateView(AgrimITCreateView):
    model = Project
    form_class = ProjectForm
    template_name = 'project_admin/project_form.html'
    success_url = reverse_lazy('projects')
    success_message = "Proyecto creado exitosamente."

# AJAX Search Example:
class ProjectSearchView(AgrimITAjaxView):
    def get_ajax_data(self):
        query = self.request.GET.get('q', '')
        projects = Project.objects.filter(
            user=self.request.user,
            client__name__icontains=query
        )[:5]
        return [{'id': p.pk, 'name': str(p)} for p in projects]
"""