import datetime
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Q

from fiscal_year.models import FiscalYear
from payout.forms import SalaryReleaseForm, SalaryTypeForm, PayoutIntervalForm
# from setup.models import Setup
from user.models import AuthUser, Payout
from utils.date_converter import english_to_nepali, nepali_str_to_english

from .models import SalaryRelease, SalaryType, PayoutInterval


# Create your views here.
class SalaryTypeListView(LoginRequiredMixin, ListView):
    model = SalaryType
    template_name = 'payout/salary_type/salary_type_list.html'
    context_object_name = 'salary_types'
    paginate_by = 10

    def get(self, request, *args, **kwargs):
        if request.GET.get('reset'):
            request.session.pop('salary_type_name', None)
            return redirect('payout:salary_type_list')
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        queryset = SalaryType.objects.all()
        name = self.request.session.get('salary_type_name', '')

        if name:
            queryset = queryset.filter(name__icontains=name)
        
        return queryset.order_by('-created_on')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['all_salary_types'] = SalaryType.objects.all().order_by('name')
        context['name'] = self.request.session.get('salary_type_name', '')
        # context['calendar_type'] = Setup.get_calendar_type()

        return context

    def post(self, request, *args, **kwargs):
        request.session['salary_type_name'] = request.POST.get('name', '')
        return self.get(request, *args, **kwargs)

class SalaryTypeCreateView(LoginRequiredMixin, CreateView):
    model = SalaryType
    form_class = SalaryTypeForm
    template_name = 'payout/salary_type/salary_type_create.html'
    success_url = reverse_lazy('payout:salary_type_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'Create'
        return context

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.created_by = self.request.user
        obj.save()
        messages.success(self.request, 'Salary type created successfully!')
        return super().form_valid(form)

class SalaryTypeUpdateView(LoginRequiredMixin, UpdateView):
    model = SalaryType
    form_class = SalaryTypeForm
    template_name = 'payout/salary_type/salary_type_create.html'
    success_url = reverse_lazy('payout:salary_type_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'Update'
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Salary type updated successfully!')
        return response

class SalaryTypeDeleteView(LoginRequiredMixin, DeleteView):
    model = SalaryType
    success_url = reverse_lazy('payout:salary_type_list')

    def get_object(self, queryset=None):
        return get_object_or_404(SalaryType, pk=self.kwargs['pk'])

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        messages.success(request, "Salary type deleted successfully.")
        return redirect(self.success_url)

#Salary Release
class SalaryReleaseListView(LoginRequiredMixin, ListView):
    model = SalaryRelease
    template_name = 'payout/salary_release/list.html'
    context_object_name = 'salary_releases'
    paginate_by = 20

    def get(self, request, *args, **kwargs):
        if request.GET.get('reset'):
            request.session.pop('employee', None)
            return redirect('payout:salary_release_list')
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        queryset = SalaryRelease.objects.all()
        employee = self.request.session.get('employee', '')

        if employee.isdigit():
            queryset = queryset.filter(employee_id=int(employee))
        
        return queryset.order_by('-created_on')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['employee_list'] = AuthUser.get_active_users()
        employee_id = self.request.session.get('employee', '')
        context['employee'] = int(employee_id) if employee_id.isdigit() else None
        return context

    def post(self, request, *args, **kwargs):
        request.session['employee'] = request.POST.get('employee', '')
        return self.get(request, *args, **kwargs)

class SalaryReleaseCreateView(LoginRequiredMixin, CreateView):
    model = SalaryRelease
    form_class = SalaryReleaseForm
    template_name = 'payout/salary_release/create_edit.html'
    success_url = reverse_lazy('payout:salary_release_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'Create'
        return context

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.created_by = self.request.user
        obj.save()
        messages.success(self.request, 'Salary release created successfully!')
        return super().form_valid(form)


class SalaryReleaseUpdateView(LoginRequiredMixin, UpdateView):
    model = SalaryRelease
    form_class = SalaryReleaseForm
    template_name = 'payout/salary_release/create_edit.html'
    success_url = reverse_lazy('payout:salary_release_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'Update'
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Salary release updated successfully!')
        return response

class SalaryReleaseDeleteView(LoginRequiredMixin, DeleteView):
    model = SalaryRelease
    success_url = reverse_lazy('payout:salary_release_list')

    def get_object(self, queryset=None):
        return get_object_or_404(SalaryRelease, pk=self.kwargs['pk'])

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        messages.success(request, "Salary release deleted successfully.")
        return redirect(self.success_url)
    

def GetStartEndDateRange(request):
    fiscal_year_id = request.GET.get('fiscal_year')
    month = request.GET.get('month')

    try:
        fiscal_year = FiscalYear.objects.get(pk=fiscal_year_id)
        month = int(month)

        nepali_range = []
        eng_fiscal_start_date = fiscal_year.start_date
        while eng_fiscal_start_date <= fiscal_year.end_date:
            nep_fiscal_start_date = english_to_nepali(eng_fiscal_start_date).strftime('%Y-%m-%d')
            _, nep_month, _ = map(int, nep_fiscal_start_date.split('-'))
            if nep_month == month:
                nepali_range.append(eng_fiscal_start_date)
            eng_fiscal_start_date += datetime.timedelta(days=1)

        if nepali_range:
            return JsonResponse({
                'start_date': english_to_nepali(nepali_range[0]).strftime('%Y-%m-%d'),
                'end_date': english_to_nepali(nepali_range[-1]).strftime('%Y-%m-%d'),
            })
        else:
            return JsonResponse({'error': 'No dates found for selected month.'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

def CalculatePayoutAmount(request):
    user_id = request.GET.get('employee')
    start_date_nep = request.GET.get('start_date')
    end_date_nep = request.GET.get('end_date')

    try:
        if not user_id or not start_date_nep or not end_date_nep:
            return JsonResponse({'calculated_amount': ''})

        user = AuthUser.objects.get(pk=user_id)
        payout = Payout.objects.filter(user=user).first()

        if not payout:
            return JsonResponse({'calculated_amount': ''})

        # Convert BS to AD
        start_date = nepali_str_to_english(start_date_nep)
        end_date = nepali_str_to_english(end_date_nep)

        # Calculate total days in the selected range
        total_days_in_month = (end_date - start_date).days + 1
        present_days_in_month = 25  # Replace with real attendance logic if needed

        if total_days_in_month <= 0:
            return JsonResponse({'calculated_amount': ''})

        # Calculate amount
        monthly_amount = payout.amount
        per_day_rate = monthly_amount / total_days_in_month
        calculated_amount = per_day_rate * present_days_in_month

        return JsonResponse({
            'calculated_amount': round(calculated_amount, 2)
        })

    except Exception as e:
        return JsonResponse({'calculated_amount': '', 'error': str(e)})



class PayoutIntervalListView(LoginRequiredMixin, ListView):
    model = PayoutInterval
    template_name = 'payout/payout_interval/payout_interval_list.html'
    context_object_name = 'intervals'
    paginate_by = 10

    def get(self, request, *args, **kwargs):
        if request.GET.get('reset'):
            request.session.pop('interval_name', None)
            return redirect('payout:interval_list')
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        queryset = PayoutInterval.objects.all()
        name = self.request.session.get('interval_name', '')

        if name:
            queryset = queryset.filter(name__icontains=name)
        
        return queryset.order_by('-created_on')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['all_intervals'] = PayoutInterval.objects.all().order_by('name')
        context['name'] = self.request.session.get('interval_name', '')
        return context

    def post(self, request, *args, **kwargs):
        request.session['interval_name'] = request.POST.get('name', '')
        return self.get(request, *args, **kwargs)

class PayoutIntervalCreateView(LoginRequiredMixin, CreateView):
    model = PayoutInterval
    form_class = PayoutIntervalForm
    template_name = 'payout/payout_interval/payout_interval_create.html'
    success_url = reverse_lazy('payout:interval_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'Create'
        return context

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Payout Interval created successfully!')
        return super().form_valid(form)

class PayoutIntervalUpdateView(LoginRequiredMixin, UpdateView):
    model = PayoutInterval
    form_class = PayoutIntervalForm
    template_name = 'payout/payout_interval/payout_interval_create.html'
    success_url = reverse_lazy('payout:interval_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'Update'
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Payout Interval updated successfully!')
        return response

class PayoutIntervalDeleteView(LoginRequiredMixin, DeleteView):
    model = PayoutInterval
    success_url = reverse_lazy('payout:interval_list')

    def get_object(self, queryset=None):
        return get_object_or_404(PayoutInterval, pk=self.kwargs['pk'])

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        messages.success(request, "Payout Interval deleted successfully.")
        return redirect(self.success_url)