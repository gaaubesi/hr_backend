from django.urls import include, path
from .views import EmployeeListView, EmployeeCreateView, EmployeeEditView, EmployeeDeleteView, EmployeeDetailView, DeleteDocumentView, DeletePayoutView, EditDocumentView, DeleteBankDetailView, EditBankDetailView

app_name = 'user'


urlpatterns = [
    path('list/', EmployeeListView.as_view(), name='employee_list'),
    path('create/', EmployeeCreateView.as_view(), name='employee_create'),
    path('edit/<int:pk>', EmployeeEditView.as_view(), name='employee_edit'),
    path('delete/<int:pk>', EmployeeDeleteView.as_view(), name='employee_delete'),
    path('detail/<int:pk>', EmployeeDetailView.as_view(), name='employee_detail'),
    path('document/<int:pk>/delete/', DeleteDocumentView.as_view(), name='delete_document'),
    path('document/<int:pk>/edit/', EditDocumentView.as_view(), name='edit_document'),
    path('payout/<int:pk>/delete/', DeletePayoutView.as_view(), name='delete_payout'),
    path('bank-detail/<int:pk>/delete/', DeleteBankDetailView.as_view(), name='delete_bank_detail'),
    path('bank-detail/<int:pk>/edit/', EditBankDetailView.as_view(), name='edit_bank_detail'),
]