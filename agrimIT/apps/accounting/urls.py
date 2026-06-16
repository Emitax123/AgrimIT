from django.urls import path
from . import views

urlpatterns = [
  path('', views.accounting_mov_display, name='accounting_display'),
  path('balance/', views.balance, name='balance'),
  path('balance/export/xlsx/', views.export_balance_xlsx, name='export_balance_xlsx'),
  path('balance/export/pdf/', views.export_balance_pdf, name='export_balance_pdf'),
  path('export/xlsx/', views.export_movements_xlsx, name='export_movements_xlsx'),
  path('invoice/<int:pk>/', views.invoice_view, name='invoice'),
  path('chart-data/', views.chart_data, name='chartdata'),
  path('balance-info/', views.balance_info, name='balance_info'),
  path('createacc/<int:pk>/', views.create_manual_acc_entry, name='accform'),
  path('<int:pk>/', views.accounting_mov_display, name='accounting_display'),
]