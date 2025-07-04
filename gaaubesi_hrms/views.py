from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy

from attendance.models import Attendance
from roster.models import Roster
from utils.date_converter import english_to_nepali
from .forms import UserLoginForm
from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.contrib.auth.views import LogoutView
from django.utils import timezone

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        current_date = timezone.now().date()
        current_time = timezone.now().time().replace(microsecond=0)

        btn_status = 'hide'
        status_type = None
        message = None
        shift_id = None

        # Check if user has leave request
        leave_requests = user.leave.filter(
            status='Approved',
            start_date__lte=current_date,
            end_date__gte=current_date
        )

        if leave_requests.exists():
            message = "You have an approved leave request for today."
            context.update({
                'btn_status': btn_status,
                'status_type': status_type,
                'message': message
            })
            return context
        
        # Get today's roster
        try:
            roster = Roster.objects.get(employee=user, date=current_date)
            roster_details = roster.roster_details.select_related('shift').all()
        except Roster.DoesNotExist:
            message = "Shift not assigned for today"
            context.update({'btn_status': btn_status, 'status_type': status_type, 'message': message})
            return context

        shift_count = roster_details.count()

        # For Only one shift
        if shift_count == 1:
            shift = roster_details[0].shift
            min_start = shift.min_start_time or shift.start_time
            max_end = shift.max_end_time or shift.end_time

            if min_start <= current_time <= max_end:
                attendance = Attendance.objects.filter(employee=user, date=current_date, shift=shift).first()
                if not attendance:
                    status_type = 'CheckIn'
                    btn_status = 'show'
                    shift_id = shift.id
                elif attendance and attendance.checkout_time:
                    status_type = None
                    btn_status = 'hide'
                    message = "You have already checked out for this shift."
                else:
                    status_type = 'CheckOut'
                    btn_status = 'show'
                    shift_id = shift.id
            else:
                message = "You are outside your shift's active time window."

        # For Multiple shifts
        elif shift_count > 1:
            current_shift = None
            for detail in roster_details:
                shift = detail.shift
                min_start = shift.min_start_time or shift.start_time
                max_end = shift.max_end_time or shift.end_time

                if min_start <= current_time <= max_end:
                    current_shift = shift
                    break

            if current_shift:
                attendance = Attendance.objects.filter(employee=user, date=current_date, shift=current_shift).first()
                if not attendance:
                    status_type = 'CheckIn'
                    btn_status = 'show'
                    shift_id = current_shift.id
                elif attendance and attendance.checkout_time:
                    status_type = None
                    btn_status = 'hide'
                    message = "You have already checked out for this shift."
                else:
                    status_type = 'CheckOut'
                    btn_status = 'show'
                    shift_id = current_shift.id
            else:
                message = "No current active shift found for now."

        context.update({
            'btn_status': btn_status,
            'status_type': status_type,
            'message': message,
            'shift_id': shift_id
        })
        return context

class LoginUserView(View):
    template_name = 'login.html'
    form_class = UserLoginForm

    def get(self, request, *args, **kwargs):
        if self.request.user.is_authenticated:
            return redirect("/")

        return render(request, self.template_name, context={'form':self.form_class()})

    def post(self, request, *args, **kwargs):
        form = UserLoginForm(request.POST)

        if form.is_valid():
            user = authenticate(
                username=form.cleaned_data.get('username'),
                password=form.cleaned_data.get('password')
            )

            # if user is not None and user.profile.role == 'Super-Admin':
            if user is not None and user.is_active:
                profile = getattr(user, 'profile', None)
                if profile and profile.status == 'not_working':
                # Block login for not working users
                    messages.error(request, "Your account is inactive because you are not working.")
                    return render(request, self.template_name, context={'form': form})
                
                next_url = self.request.GET.get('next')
                login(self.request, user)
                if next_url:
                    return redirect(next_url)
                return redirect('/')   
            else:
                messages.error(self.request, 'Invalid login credentials')


        return render(request, self.template_name, context={'form':form})


class UserLogoutView(LogoutView):
    next_page = reverse_lazy('login')
