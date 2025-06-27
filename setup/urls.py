from django.urls import path
from . import views

app_name = 'setup'

urlpatterns = [
    path('list/', views.SetupListView.as_view(), name='setup_list'),
    path('create/', views.SetupCreateView.as_view(), name='setup_create'),
    path('edit/<int:pk>/', views.SetupUpdateView.as_view(), name='setup_edit'),
    path('delete/<int:pk>/', views.SetupDeleteView.as_view(), name='setup_delete'),
] 