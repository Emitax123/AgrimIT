from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
import logging

logger = logging.getLogger(__name__)


class TenantMixin(LoginRequiredMixin):
    """
    Automatically filter querysets by current user ownership.
    Use this as base for all user-specific data views.
    """
    
    def get_queryset(self):
        """Filter queryset to only show objects owned by current user"""
        queryset = super().get_queryset()
        if hasattr(queryset.model, 'user'):
            return queryset.filter(user=self.request.user)
        return queryset

    def form_valid(self, form):
        """Automatically set user when creating new objects"""
        if hasattr(form.instance, 'user'):
            form.instance.user = self.request.user
            logger.info(f"Object created by user {self.request.user.id}", extra={
                'user_id': self.request.user.id,
                'model': form.instance.__class__.__name__,
                'object_id': getattr(form.instance, 'pk', 'new')
            })
        return super().form_valid(form)


class AgrimITBaseView(TenantMixin):
    """
    Base view for all AgrimIT views with common context data.
    Includes user statistics and common template variables.
    """
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add common context for all views
        user = self.request.user
        context.update({
            'clients_count': user.clients.filter(flag=True).count(),
            'projects_count': user.projects.count(),
            'user_name': user.get_full_name() or user.username,
        })
        
        return context


class AjaxResponseMixin:
    """
    Mixin to handle AJAX requests with JSON responses.
    """
    
    def dispatch(self, request, *args, **kwargs):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return self.ajax_response(request, *args, **kwargs)
        return super().dispatch(request, *args, **kwargs)
    
    def ajax_response(self, request, *args, **kwargs):
        """Override this method to handle AJAX requests"""
        return JsonResponse({'error': 'AJAX handler not implemented'}, status=501)


class MessageMixin:
    """
    Mixin to handle success/error messages consistently.
    """
    success_message = None
    error_message = None
    
    def form_valid(self, form):
        response = super().form_valid(form)
        if self.success_message:
            messages.success(self.request, self.success_message)
        return response
    
    def form_invalid(self, form):
        response = super().form_invalid(form)
        if self.error_message:
            messages.error(self.request, self.error_message)
        return response


class BulkActionMixin:
    """
    Mixin for handling bulk actions on multiple objects.
    """
    bulk_actions = {}  # {'action_name': 'method_name'}
    
    def post(self, request, *args, **kwargs):
        action = request.POST.get('bulk_action')
        selected_ids = request.POST.getlist('selected_objects')
        
        if action and action in self.bulk_actions and selected_ids:
            method_name = self.bulk_actions[action]
            method = getattr(self, method_name, None)
            if method:
                return method(selected_ids)
        
        return super().post(request, *args, **kwargs)


class SearchMixin:
    """
    Mixin to handle search functionality in list views.
    """
    search_fields = []  # Fields to search in
    search_param = 'q'  # URL parameter for search query
    
    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get(self.search_param)
        
        if search_query and self.search_fields:
            from django.db.models import Q
            search_filter = Q()
            
            for field in self.search_fields:
                search_filter |= Q(**{f"{field}__icontains": search_query})
            
            queryset = queryset.filter(search_filter)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get(self.search_param, '')
        return context


class FilterMixin:
    """
    Mixin to handle filtering in list views.
    """
    filter_fields = {}  # {'filter_name': 'model_field'}
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        for filter_name, model_field in self.filter_fields.items():
            filter_value = self.request.GET.get(filter_name)
            if filter_value:
                queryset = queryset.filter(**{model_field: filter_value})
        
        return queryset


class TransactionMixin:
    """
    Mixin to wrap form processing in database transaction.
    """
    
    @transaction.atomic
    def form_valid(self, form):
        return super().form_valid(form)


# Utility functions
def get_user_object_or_404(model, user, **kwargs):
    """Get object that belongs to user or raise 404"""
    return get_object_or_404(model, user=user, **kwargs)


def paginate_queryset_cbv(queryset, request, per_page=12):
    """
    Utility function for manual pagination in CBVs.
    Use built-in ListView.paginate_by when possible.
    """
    paginator = Paginator(queryset, per_page)
    page = request.GET.get('page')
    
    try:
        paginated = paginator.page(page)
    except PageNotAnInteger:
        paginated = paginator.page(1)
    except EmptyPage:
        paginated = paginator.page(paginator.num_pages)
    
    return paginated, paginator