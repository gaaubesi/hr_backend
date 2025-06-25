from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q
from .models import Setup
from .forms import SetupForm

# Create your views here.

class SetupView(LoginRequiredMixin, CreateView):
    model = Setup
    form_class = SetupForm
    template_name = 'setup/setup_form.html'
    success_url = reverse_lazy('setup:setup_form')

    def get_object(self, queryset=None):
        # Try to get the first (and only) setup object
        return Setup.objects.first()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        setup = self.get_object()
        if setup:
            context['action'] = 'Update'
            context['setup'] = setup
        else:
            context['action'] = 'Create'
        return context

    def form_valid(self, form):
        setup = self.get_object()
        if setup:
            # Update existing setup
            setup.calendar_type = form.cleaned_data['calendar_type']
            setup.shift_threshold = form.cleaned_data['shift_threshold']
            setup.save()
            messages.success(self.request, 'Setup updated successfully!')
            return redirect(self.success_url)
        else:
            # Create new setup
            messages.success(self.request, 'Setup created successfully!')
            return super().form_valid(form)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        setup = self.get_object()
        if setup:
            # Pre-populate form with existing data
            form.initial = {
                'calendar_type': setup.calendar_type,
                'shift_threshold': setup.shift_threshold,
            }
        return form
