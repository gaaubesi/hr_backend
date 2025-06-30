from django.urls import path
from . import views

app_name = 'setup'

urlpatterns = [
    path('', views.SetupView.as_view(), name='setup_form'),
] 