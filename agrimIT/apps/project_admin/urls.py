from django.urls import path, include
from . import views
  
urlpatterns = [
  path('', views.index, name = 'index'),
  path('projects/', views.projectlist_view, name = 'projects'),
  path('listprojects/<int:pk>', views.alt_projectlist_view, name = 'projectslist'),
  path('listprojectstype/<int:type>', views.projectlistfortype_view, name = 'projectslisttype'),
  path('create/', views.create_view, name = 'create'),
  path('delete/<int:pk>', views.delete_view, name = 'delete'),
  path('close/<int:pk>', views.close_view, name = 'close'),
  path('upload/<int:pk>', views.upload_files, name= 'upload'),
  path('download/<int:pk>/', views.download_file, name='download'),
  path('deletefile/<int:pk>', views.delete_file, name='deletefile'),
  path('filesview/<int:pk>', views.file_view, name = 'files'),
  path('project/<int:pk>',views.project_view, name= 'projectview'),
  path('project/mod/<int:pk>', views.mod_view, name= 'modification',),
  path('project/modify/<int:pk>', views.full_mod_view, name='fullmodification'),
  path('history', views.history_view, name='history'),
  path('search/', views.search, name='search'),
  path('generate-test-data/', views.generate_test_data, name='generate_test_data'), 
  path('generate-monthly-summaries/', views.generate_monthly_summaries, name='generate_monthly_summaries'),
]