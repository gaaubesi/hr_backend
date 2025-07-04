from django.urls import path
from . import views

app_name = 'payout'

urlpatterns = [
    # Salary Type
    path('salary-type/list/', views.SalaryTypeListView.as_view(), name='salary_type_list'),
    path('salary-type/create/', views.SalaryTypeCreateView.as_view(), name='salary_type_create'),
    path('salary-type/edit/<int:pk>/', views.SalaryTypeUpdateView.as_view(), name='salary_type_edit'),
    path('salary-type/delete/<int:pk>/', views.SalaryTypeDeleteView.as_view(), name='salary_type_delete'),

    # Salary Release
    path('salary-release/list/', views.SalaryReleaseListView.as_view(), name='salary_release_list'),
    path('salary-release/create/', views.SalaryReleaseCreateView.as_view(), name='salary_release_create'),
    path('salary-release/edit/<int:pk>/', views.SalaryReleaseUpdateView.as_view(), name='salary_release_edit'),
    path('salary-release/delete/<int:pk>/', views.SalaryReleaseDeleteView.as_view(), name='salary_release_delete'),

    #Ajax URLs for Salary Release
    path('ajax/get-start-end-date-range/', views.GetStartEndDateRange, name='get_start_end_date_range'),
    path('ajax/calculate-payout-amount/', views.CalculatePayoutAmount, name='calculate_payout_amount'),

    # Payout Interval
    path('interval/list/', views.PayoutIntervalListView.as_view(), name='interval_list'),
    path('interval/create/', views.PayoutIntervalCreateView.as_view(), name='interval_create'),
    path('interval/edit/<int:pk>/', views.PayoutIntervalUpdateView.as_view(), name='interval_edit'),
    path('interval/delete/<int:pk>/', views.PayoutIntervalDeleteView.as_view(), name='interval_delete'),
] 