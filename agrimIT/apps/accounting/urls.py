from django.urls import path
from . import views

urlpatterns = [
  path('', views.accounting_mov_display, name='accounting_display'),
  path('<int:pk>/', views.accounting_mov_display, name='accounting_display'),
  path('balance/', views.balance, name='balance'),
  path('chart-data/', views.chart_data, name='chartdata'),
  path('balance-info/', views.balance_info, name='balance_info'),
  path('createacc/<int:pk>/', views.create_manual_acc_entry, name='accform'),
]