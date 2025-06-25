from django.shortcuts import render
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.db.models import Q
from .models import Setup
from .forms import SetupForm

# Create your views here.

class SetupListView(LoginRequiredMixin, ListView):
    model = Setup
    template_name = 'setup/setup_list.html'
    context_object_name = 'setups'
    paginate_by = 10

    def get(self, request, *args, **kwargs):
        if request.GET.get('reset'):
            request.session.pop('calendar_type', None)
            return redirect('setup:setup_list')
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Setup.objects.all()
        calendar_type = self.request.session.get('calendar_type', '')

        if calendar_type:
            queryset = queryset.filter(calendar_type=calendar_type)
        
        return queryset.order_by('-created_on')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['calendar_choices'] = Setup.CALENDAR_CHOICES
        context['calendar_type'] = self.request.session.get('calendar_type', '')
        return context

    def post(self, request, *args, **kwargs):
        request.session['calendar_type'] = request.POST.get('calendar_type', '')
        return self.get(request, *args, **kwargs)


class SetupCreateView(LoginRequiredMixin, CreateView):
    model = Setup
    form_class = SetupForm
    template_name = 'setup/setup_create.html'
    success_url = reverse_lazy('setup:setup_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'Create'
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Setup created successfully!')
        return super().form_valid(form)

class SetupUpdateView(LoginRequiredMixin, UpdateView):
    model = Setup
    form_class = SetupForm
    template_name = 'setup/setup_create.html'
    success_url = reverse_lazy('setup:setup_list')
    

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'Update'
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Setup updated successfully!')
        return response

class SetupDeleteView(LoginRequiredMixin, DeleteView):
    model = Setup
    success_url = reverse_lazy('setup:setup_list')

    def get_object(self, queryset=None):
        return get_object_or_404(Setup, pk=self.kwargs['pk'])

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        messages.success(request, "Setup deleted successfully.")
        return redirect(self.success_url)
