from django.urls import path, include
from . import views

urlpatterns = [
    path('users/', include ('apps.users.urls')), 
    path('clients/', views.clients_view, name='clients'),
    path('clients/create', views.create_client_view, name='clientcreate'),
    path('clients/projectcreate/<int:pk>', views.create_for_client, name='clientprojectcreate'),
    path('create/clientedislist/<int:pk>', views.clientedislist, name='clientedislist'),
    path('create/deleteclient/<int:pk>', views.deleteclient, name='deleteclient'),
]
