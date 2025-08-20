from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404

class TenantMixin(LoginRequiredMixin):
    """Automatically filter querysets by current user ownership"""
    
    def get_queryset(self):
        """Filter queryset to only show objects owned by current user"""
        queryset = super().get_queryset()
        return queryset.filter(user=self.request.user)

    def form_valid(self, form):
        """Automatically set user when creating new objects"""
        if hasattr(form.instance, 'user'):
            form.instance.user = self.request.user
        return super().form_valid(form)

def get_user_object_or_404(model, user, **kwargs):
    """Get object that belongs to user or raise 404"""
    return get_object_or_404(model, user=user, **kwargs)