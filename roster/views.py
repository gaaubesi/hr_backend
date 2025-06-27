from django.http import JsonResponse
from django.utils import timezone

from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView

from department.models import Department
from leave.models import Leave, LeaveType
from user.models import AuthUser
from .models import Roster, RosterDetail, Shift
from .forms import ShiftForm
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin 
from django.contrib import messages
from utils.date_converter import english_to_nepali, nepali_str_to_english
from collections import defaultdict
from django.db.models import Prefetch
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from datetime import datetime, timedelta

class ShiftListView(ListView):
    model = Shift
    template_name = 'roster/shift/list.html'
    context_object_name = 'shifts'
    paginate_by = 10

    def get_queryset(self):
        queryset = Shift.objects.all().order_by('-id')
        
        # Get filter parameters from either POST or GET
        request_data = self.request.POST if self.request.method == 'POST' else self.request.GET
        
        title = request_data.get('title')

        # Apply filters
        if title:
            queryset = queryset.filter(title__icontains=title)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get list of titles for the select dropdown
        context['titles'] = Shift.objects.values_list('title', flat=True).distinct().order_by('title')
        
        # Add current filter values to context from either POST or GET
        request_data = self.request.POST if self.request.method == 'POST' else self.request.GET
        context['current_title'] = request_data.get('title', '')
        
        return context

    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)
    

class ShiftCreateView(LoginRequiredMixin, CreateView):
    model = Shift
    form_class = ShiftForm
    template_name = 'roster/shift/create.html'
    success_url = reverse_lazy('roster:shift_list')

    def form_valid(self, form):
        shift = form.save(commit=False)
        shift.created_by = self.request.user
        shift.save()
        messages.success(self.request, "Shift created successfully.")
        return redirect(self.success_url)


class ShiftEditView(LoginRequiredMixin, UpdateView):
    model = Shift
    form_class = ShiftForm
    template_name = 'roster/shift/edit.html'
    success_url = reverse_lazy('roster:shift_list')

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Shift updated successfully.")
        return redirect(self.success_url)

class ShiftDeleteView(View):
    model = Shift
    success_url = reverse_lazy('roster:shift_list')
    
    def get_object(self, queryset=None):
        return get_object_or_404(Shift, pk=self.kwargs['pk'])

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        messages.success(request, "Shift deleted successfully.")
        return redirect(self.success_url)
    
def get_week_days(selected_date):
    # Get ISO calendar details
    year, week, day = selected_date.isocalendar()
    week_days = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]

    # Determine the start of the week (Sunday)
    start_of_week = selected_date - timedelta(days=(day % 7))  # Align to Sunday

    # Generate all days of the week starting from Sunday
    week_info = [(start_of_week + timedelta(days=i), week_days[i]) for i in range(7)]
    return week_info

class RosterListView(ListView):
    model = Roster  
    template_name = 'roster/roster/list.html'
    context_object_name = 'rosters'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        input_date = self.request.GET.get("date")
        department_id = self.request.GET.get("department")
        employee_id = self.request.GET.get("employee")
        employee_id = str(employee_id) if employee_id else None

        if input_date:
            try:
                date = nepali_str_to_english(input_date)
            except Exception:
                date = timezone.now().date()
        else:
            date = timezone.now().date()
            input_date = english_to_nepali(date)

        week_info = get_week_days(date)

        # Calculate max allowed date (end of next week)
        current_week_info = get_week_days(timezone.now().date())
        min_allowed_eng_date = current_week_info[0][0]
        min_allowed_nep = english_to_nepali(min_allowed_eng_date)
        max_allowed_eng_date = current_week_info[-1][0] + timedelta(days=7)
        max_allowed_nep = english_to_nepali(max_allowed_eng_date)


        # Get users
        all_users_qs = AuthUser.get_active_users()
        if department_id:
            all_users_qs = all_users_qs.filter(working_detail__department_id=department_id)
        
        filtered_users_qs = all_users_qs
        if employee_id:
            filtered_users_qs = all_users_qs.filter(id=employee_id)
        
        # Fetch rosters + shifts for the week in a single query
        start_date, end_date = week_info[0][0], week_info[-1][0]
        roster_qs = Roster.objects.filter(
            date__range=[start_date, end_date],
            employee__in=filtered_users_qs
        ).prefetch_related(
            Prefetch('roster_details', queryset=RosterDetail.objects.select_related('shift'))
        )

        # Build roster_map: {employee_id: {date: [details]}}
        roster_map = defaultdict(lambda: defaultdict(list))
        for roster in roster_qs:
            for detail in roster.roster_details.all():
                roster_map[roster.employee.id][roster.date].append(detail)

        # Add context
        context.update({
            'all_departments': Department.objects.all().order_by('name'),
            'all_users': all_users_qs.order_by('first_name'),
            'filtered_users': filtered_users_qs.order_by('first_name'),
            'team_member_count': filtered_users_qs.count(),
            'all_shifts': Shift.objects.all().order_by('title'),
            'days': week_info,
            'min_allowed_date_nep': min_allowed_nep,
            'max_allowed_date_nep': max_allowed_nep,
            'selected_date': input_date,
            'selected_department': department_id,
            'selected_employee': employee_id,
            'roster_map': roster_map,
        })
        return context

@require_POST
@csrf_exempt
def add_shift_ajax(request):
    employee_id = request.POST.get("employee_id")
    shift_id = request.POST.get("shift_id")
    date_str = request.POST.get("date")

    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()

        # Get the shift
        shift = Shift.objects.get(id=shift_id)
        shift_title = shift.title.strip().lower()

        # Try to get an existing Roster or create one
        roster = Roster.objects.filter(employee_id=employee_id, date=date).first()
        if not roster:
            roster = Roster.objects.create(
                employee_id=employee_id,
                date=date,
                created_by=request.user
            )

        # Prevent duplicate shift
        if RosterDetail.objects.filter(roster=roster, shift=shift).exists():
            return JsonResponse({
                "success": False,
                "error": "This shift has already been assigned to the employee for the selected date."
            }, status=400)

        # Create RosterDetail
        RosterDetail.objects.create(
            roster=roster,
            shift=shift,
            created_by=request.user
        )

        # Handle Weekly Shift Leave
        if shift_title == 'weekly shift':
            leave_type = LeaveType.objects.filter(code='weekly').first()
            if leave_type:
                leave_exists = Leave.objects.filter(
                employee_id=employee_id,
                start_date=date,
                end_date=date,
                leave_type_id=leave_type.id
            ).exclude(status='Declined').exists()


                if not leave_exists:
                    Leave.objects.create(
                        employee_id=employee_id,
                        leave_type=leave_type,
                        start_date=date,
                        end_date=date,
                        no_of_days=1,
                        reason="Weekly Shift Leave",
                        status="Approved",
                        created_by=request.user
                    )

        return JsonResponse({"success": True})

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@require_POST
@csrf_exempt
def ajax_edit_shift(request):
    detail_id = request.POST.get("detail_id")
    new_shift_id = request.POST.get("shift_id")
    roster_id = request.POST.get("roster_id")

    try:
        # Check for duplicate shift in the same roster
        if RosterDetail.objects.filter(roster_id=roster_id, shift_id=new_shift_id).exclude(id=detail_id).exists():
            return JsonResponse({"success": False, "error": "This shift already exists for the selected date."})

        # Fetch and update the shift detail
        detail = RosterDetail.objects.select_related('roster__employee', 'shift').get(id=detail_id)
        old_shift_title = detail.shift.title.lower().strip()
        detail.shift_id = new_shift_id
        # detail.updated_on = timezone.now()
        detail.updated_by = request.user
        detail.save()

        # Get new shift, employee, and date
        new_shift = Shift.objects.get(id=new_shift_id)
        new_shift_title = new_shift.title.lower().strip()
        employee = detail.roster.employee
        date = detail.roster.date

        # Fetch the weekly leave type
        leave_type = LeaveType.objects.filter(code='weekly').first()

        if leave_type:
            # 🟢 If new shift is 'Weekly Shift' → create leave if not exists
            if new_shift_title == 'weekly shift':
                leave_exists = Leave.objects.filter(
                    employee=employee,
                    start_date=date,
                    end_date=date,
                    leave_type=leave_type
                ).exclude(status='Declined').exists()

                if not leave_exists:
                    Leave.objects.create(
                        employee=employee,
                        leave_type=leave_type,
                        start_date=date,
                        end_date=date,
                        no_of_days=1,
                        reason="Weekly Shift Leave",
                        status="Approved",
                        created_by=request.user
                    )

            # 🔴 If old shift was 'Weekly Shift' but new shift is not → delete leave
            elif old_shift_title == 'weekly shift' and new_shift_title != 'weekly shift':
                Leave.objects.filter(
                    employee=employee,
                    start_date=date,
                    end_date=date,
                    leave_type=leave_type
                ).delete()

        return JsonResponse({"success": True})

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)

@require_POST
@csrf_exempt
def delete_shift_ajax(request):
    detail_id = request.POST.get("detail_id")

    try:
        detail = RosterDetail.objects.select_related('roster', 'shift').get(id=detail_id)
        employee = detail.roster.employee
        shift_title = detail.shift.title.strip().lower()
        date = detail.roster.date

        # Delete the RosterDetail
        detail.delete()

        # If the shift is a weekly shift, delete the leave as well
        if shift_title == 'weekly shift':
            leave_type = LeaveType.objects.filter(code='weekly').first()
            if leave_type:
                Leave.objects.filter(
                    employee=employee,
                    leave_type=leave_type,
                    start_date=date,
                    end_date=date
                ).exclude(status='Declined').delete()

        return JsonResponse({"success": True})

    except RosterDetail.DoesNotExist:
        return JsonResponse({"success": False, "error": "Shift not found."}, status=404)

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)

    
def get_employees_by_department(request):
    dept_id = request.GET.get("department_id")
    if dept_id:
        users = AuthUser.objects.filter(is_active=True, working_detail__department_id=dept_id).order_by("first_name")
    else:
        users = AuthUser.objects.filter(is_active=True).order_by("first_name")

    user_list = list(users.values("id", "first_name", "last_name"))
    return JsonResponse({"employees": user_list})

    
