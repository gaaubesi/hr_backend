from django.shortcuts import render
from django.db import transaction
from django.utils import timezone
from django.contrib import messages
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect
from datetime import date,datetime
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView
from django.views.generic.edit import DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
import nepali_datetime

from department.models import Department
from fiscal_year.models import FiscalYear
from leave.models import Leave
from roster.models import Roster, RosterDetail, Shift
from setup.models import Setup
from user.models import AuthUser
from utils.date_converter import english_to_nepali
from utils.enums import NepaliMonthList 
from .models import Request, RequestStatus, RequestType, Attendance
from .forms import RequestForm

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from datetime import timedelta
from collections import defaultdict

class CheckInView(View):
    def post(self, request):
        user = request.user
        today = timezone.now().date()
        now = timezone.now()

        lat = request.POST.get('checkinlat')
        lon = request.POST.get('checkinlon')
        shift_id = request.POST.get('shift_id')

        # if not shift_id:
        #     messages.error(request, "Shift ID missing.")
        #     return redirect(reverse_lazy('dashboard'))

        try:
            shift = Shift.objects.get(id=shift_id)
        except Shift.DoesNotExist:
            messages.error(request, "Invalid shift.")
            return redirect(reverse_lazy('dashboard'))

        # Try to get existing attendance record for this shift and date
        attendance, created = Attendance.objects.get_or_create(
            employee=user,
            date=today,
            shift=shift,
            defaults={
                'actual_checkin_time': now.time().replace(microsecond=0),
                'checkin_time': now.time().replace(microsecond=0),
            }
        )

        if not created:
            # Already exists — update check-in fields
            attendance.actual_checkin_time = now.time().replace(microsecond=0)

        # Apply approved late arrival time if applicable
        approved_late_request = Request.objects.filter(
            employee=user,
            date=today,
            type=RequestType.LATE_ARRIVAL_REQUEST,
            status=RequestStatus.APPROVED
        ).first()

        checkin_time = approved_late_request.time if approved_late_request else now.time().replace(microsecond=0)

        # Respect shift start time if earlier
        if checkin_time < shift.start_time:
            checkin_time = shift.start_time

        attendance.checkin_time = checkin_time

        # Update location if available
        try:
            if lat and lon:
                attendance.checkin_location = {
                    'type': 'Point',
                    'coordinates': [round(float(lon), 6), round(float(lat), 6)]
                }
        except (ValueError, TypeError):
            messages.warning(request, "Invalid location data received.")

        attendance.save()

        msg = "Check-In Successful" if created else "Check-In Updated for this shift"
        messages.success(request, msg)
        return redirect(reverse_lazy('dashboard'))



class CheckoutView(View):
    def post(self, request):
        user = request.user
        today = timezone.now().date()
        now = timezone.now()

        shift_id = request.POST.get("shift_id")
        lat = request.POST.get("checkoutlat")
        lon = request.POST.get("checkoutlon")

        # if not shift_id:
        #     messages.error(request, "Missing shift ID.")
        #     return redirect(reverse_lazy("dashboard"))

        try:
            shift = Shift.objects.get(id=shift_id)
        except Shift.DoesNotExist:
            messages.error(request, "Invalid shift.")
            return redirect(reverse_lazy("dashboard"))

        # Try to get existing attendance for this shift
        attendance, created = Attendance.objects.get_or_create(
            employee=user,
            date=today,
            shift=shift,
            defaults={
                "actual_checkin_time": None,
                "checkin_time": None,
            }
        )

        # Set checkout times
        attendance.actual_checkout_time = now.time().replace(microsecond=0)
        checkout_time = now.time().replace(microsecond=0)

        # Apply early departure request
        approved_request = Request.objects.filter(
            employee=user,
            date=today,
            type=RequestType.EARLY_DEPARTURE_REQUEST,
            status=RequestStatus.APPROVED
        ).first()

        if approved_request:
            checkout_time = approved_request.time

        # Clamp checkout time to shift end
        if shift.end_time and checkout_time > shift.end_time:
            checkout_time = shift.end_time

        attendance.checkout_time = checkout_time

        # Calculate working hours if checkin exists
        if attendance.checkin_time and checkout_time:
            attendance.working_hours = calculate_working_hours(attendance.checkin_time, checkout_time)

        # Save checkout location
        try:
            if lat and lon:
                attendance.checkout_location = {
                    "type": "Point",
                    "coordinates": [round(float(lon), 6), round(float(lat), 6)]
                }
        except (ValueError, TypeError):
            messages.warning(request, "Invalid location data received.")

        attendance.save()

        if created:
            messages.success(request, "New attendance record created with Check-Out.")
        else:
            messages.success(request, "Check-Out updated for this shift.")

        return redirect(reverse_lazy("dashboard"))

# Attendance Request
class AttendanceRequestListView(ListView):
    model = Request  
    template_name = 'attendance/request/request_list.html'
    context_object_name = 'requests'
    paginate_by = 10 
    def get_queryset(self):
        queryset = Request.objects.select_related('employee').all()
        
        # Apply filters if POST request
        if self.request.method == 'POST':
            employee_id = self.request.POST.get('employee')
            status = self.request.POST.get('status')
            
            if employee_id:
                queryset = queryset.filter(employee_id=employee_id)
            if status:
                queryset = queryset.filter(status=status)
        
        return queryset.order_by('-id')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['request_status_choices'] = RequestStatus.choices
        # context['employees'] = self.request.user.__class__.objects.all()  # Get all users
        context['employees'] = AuthUser.get_active_users()
        context['calendar_type'] = Setup.get_calendar_type()
        
        # Add current filter values to context
        if self.request.method == 'POST':
            context['employee'] = self.request.POST.get('employee')
            context['status'] = self.request.POST.get('status')
        
        return context
    
    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)

class AttendanceRequestCreateView(LoginRequiredMixin, CreateView):
    model = Request
    form_class = RequestForm
    template_name = 'attendance/request/request_create.html'
    success_url = reverse_lazy('attendance:request_list')

    def form_valid(self, form):
        attendance_request = form.save(commit=False)
        attendance_request.created_by = self.request.user
        attendance_request.employee_id = self.request.user.id
        attendance_request.save()
        messages.success(self.request, "Request created successfully.")
        return redirect(self.success_url)


class AttendanceRequestEditView(LoginRequiredMixin, UpdateView):
    model = Request
    form_class = RequestForm
    template_name = 'attendance/request/request_edit.html'
    success_url = reverse_lazy('attendance:request_list')

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Request updated successfully.")
        return redirect(self.success_url)

class AttendanceRequestDeleteView(View):
    model = Request
    success_url = reverse_lazy('attendance:request_list')
    
    def get_object(self, queryset=None):
        return get_object_or_404(Request, pk=self.kwargs['pk'])

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        messages.success(request, "Request deleted successfully.")
        return redirect(self.success_url)
    
    
class RequestUpdateStatusView(View):
    def post(self, request, pk):
        req = get_object_or_404(Request, pk=pk)
        new_status = request.POST.get('status')

        valid_statuses = dict(RequestStatus.choices).keys()
        if not new_status or new_status not in valid_statuses:
            messages.error(request, 'Invalid status selected.')
            return redirect('attendance:request_list')

        req.status = new_status
        req.save()

        if new_status == RequestStatus.APPROVED:
            update_attendance_for_request(req)

        messages.success(request, f'Status updated to {req.get_status_display()}.')
        return redirect('attendance:request_list')

    def get(self, request, pk):
        # Optional: prevent direct GET requests
        return redirect('attendance:request_list')


def update_attendance_for_request(req):
    updated = False
    request_time = req.time

    try:
        # Get roster for the employee on that date
        roster = Roster.objects.get(date=req.date, employee=req.employee)
        roster_details = roster.roster_details.select_related('shift').all()
    except Roster.DoesNotExist:
        roster_details = []

    # If only one shift → use it directly
    if len(roster_details) == 1:
        shift = roster_details[0].shift
        attendance = Attendance.objects.filter(
            employee=req.employee,
            date=req.date,
            shift=shift
        ).first()

    # If multiple shifts, find the matching one based on request time
    elif len(roster_details) > 1 and request_time:
        shift = None
        for rd in roster_details:
            s = rd.shift
            min_start = s.min_start_time or s.start_time
            max_end = s.max_end_time or s.end_time

            if min_start <= request_time <= max_end:
                shift = s
                break

        if shift:
            attendance = Attendance.objects.filter(
                employee=req.employee,
                date=req.date,
                shift=shift
            ).first()
        else:
            attendance = None
    else:
        attendance = None

    # Update the matched attendance (if found)
    if attendance:
        if req.type == RequestType.LATE_ARRIVAL_REQUEST and attendance.checkin_time:
            attendance.checkin_time = req.time
            updated = True

        elif req.type == RequestType.EARLY_DEPARTURE_REQUEST and attendance.checkout_time:
            attendance.checkout_time = req.time
            updated = True

        elif req.type == RequestType.MISSED_CHECKOUT:
            attendance.checkout_time = req.time
            updated = True

        if updated and attendance.checkin_time and attendance.checkout_time:
            attendance.working_hours = calculate_working_hours(
                attendance.checkin_time, attendance.checkout_time
            )

        if updated:
            attendance.save()

    # Fallback to attendance with no shift assigned (edge cases)
    # if not updated:
    #     attendance = Attendance.objects.filter(
    #         employee=req.employee,
    #         date=req.date,
    #         shift__isnull=True
    #     ).first()

    #     if attendance:
    #         if req.type == RequestType.LATE_ARRIVAL_REQUEST and attendance.checkin_time:
    #             attendance.checkin_time = req.time
    #             updated = True

    #         elif req.type == RequestType.EARLY_DEPARTURE_REQUEST and attendance.checkout_time:
    #             attendance.checkout_time = req.time
    #             updated = True

    #         elif req.type == RequestType.MISSED_CHECKOUT:
    #             attendance.checkout_time = req.time
    #             updated = True

    #         if updated and attendance.checkin_time and attendance.checkout_time:
    #             attendance.working_hours = calculate_working_hours(
    #                 attendance.checkin_time, attendance.checkout_time
    #             )

    #         if updated:
    #             attendance.save()



def calculate_working_hours(checkin_time, checkout_time):
    if checkin_time and checkout_time:
        start = datetime.combine(date.today(), checkin_time)
        end = datetime.combine(date.today(), checkout_time)
        return (end - start).total_seconds() / 3600
    return 0


class CalendarViewReport(LoginRequiredMixin, ListView):
    model = Attendance
    template_name = 'attendance/report/calendar_view_report.html'
    context_object_name = 'attendances'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        request = self.request
        department_id = request.GET.get("department")
        employee_id = request.GET.get("employee") if request.GET.get("employee") else request.user.id
        fiscal_year = request.GET.get("fiscal_year")

        # Handle fiscal year filtering
        if not fiscal_year:
            current_fiscal = FiscalYear.current_fiscal_year()
            fiscal_year = current_fiscal.id if current_fiscal else None
        else:
            fiscal_year = int(fiscal_year)

        nep_date = nepali_datetime.date.today()

        try:
            bs_month = int(request.GET.get("month")) if request.GET.get("month") else nep_date.month
        except ValueError:
            bs_month = nep_date.month

        bs_year = nep_date.year

        try:
            days_in_month = nepali_datetime._days_in_month(bs_year, bs_month)
        except Exception as e:
            days_in_month = 30
            print(f"Error determining days in month: {e}")

        start_ad_date = nepali_datetime.date(bs_year, bs_month, 1).to_datetime_date()
        end_ad_date = nepali_datetime.date(bs_year, bs_month, days_in_month).to_datetime_date()

        attendance_dict = {
            (start_ad_date + timedelta(days=n)): []
            for n in range((end_ad_date - start_ad_date).days + 1)
        }

        attendance_qs = Attendance.objects.filter(
            employee_id=employee_id, date__range=(start_ad_date, end_ad_date)
        ).select_related('shift')

        rosters = Roster.objects.filter(
            employee_id=employee_id, date__range=(start_ad_date, end_ad_date)
        ).prefetch_related('roster_details__shift')

        leave_qs = Leave.objects.filter(
            employee_id=employee_id,
            status='Approved',
            start_date__lte=end_ad_date,
            end_date__gte=start_ad_date
        ).select_related('leave_type')

        # Filter by fiscal year if selected
        if fiscal_year:
            try:
                selected_fiscal = FiscalYear.objects.get(id=fiscal_year)
                # Filter attendance data within fiscal year range
                attendance_qs = attendance_qs.filter(
                    date__range=(selected_fiscal.start_date, selected_fiscal.end_date)
                )
                # Filter roster data within fiscal year range
                rosters = rosters.filter(
                    date__range=(selected_fiscal.start_date, selected_fiscal.end_date)
                )
                # Filter leave data within fiscal year range
                leave_qs = leave_qs.filter(
                    start_date__lte=selected_fiscal.end_date,
                    end_date__gte=selected_fiscal.start_date
                )
            except FiscalYear.DoesNotExist:
                pass

        first_day_weekday = (start_ad_date.weekday() + 1) % 7
        empty_days = [''] * first_day_weekday

        for single_date in attendance_dict.keys():
            day_roster = next((r for r in rosters if r.date == single_date), None)
            shifts = day_roster.roster_details.all() if day_roster else []

            for shift_detail in shifts:
                shift = shift_detail.shift
                att = next(
                    (a for a in attendance_qs if a.date == single_date and a.shift_id == shift.id),
                    None
                )

                if att:
                    if att.actual_checkin_time and att.actual_checkout_time:
                        status = "CheckedOut"
                    elif att.actual_checkin_time:
                        status = "CheckedIn"
                    else:
                        status = "-"
                    attendance_dict[single_date].append(f"{shift.title} ({status})")
                else:
                    attendance_dict[single_date].append(f"{shift.title} (No Attendance)")

            if not attendance_dict[single_date]:
                leave = next((l for l in leave_qs if l.start_date <= single_date <= l.end_date), None)
                if leave:
                    if leave.leave_type and leave.leave_type.code and leave.leave_type.code.lower() == 'weekly':
                        attendance_dict[single_date].append("Weekly Leave")
                    else:
                        attendance_dict[single_date].append("On Leave")

        # Filter users
        all_users_qs = AuthUser.get_active_users()
        if department_id:
            all_users_qs = all_users_qs.filter(working_detail__department_id=department_id)
        filtered_users_qs = all_users_qs
        if employee_id:
            filtered_users_qs = filtered_users_qs.filter(id=employee_id)

        context.update({
            'all_departments': Department.objects.all().order_by('name'),
            'all_users': all_users_qs.order_by('first_name'),
            'filtered_users': filtered_users_qs.order_by('first_name'),
            'nepali_months': NepaliMonthList,
            'selected_department': department_id,
            'selected_employee': str(employee_id),
            'fiscal_year': fiscal_year,
            'fiscal_years': FiscalYear.objects.filter(status='active'),
            'year': bs_year,
            'selected_month': int(bs_month),
            'days_in_month': range(1, days_in_month + 1),
            'attendance_dict': attendance_dict,
            'first_day_weekday': first_day_weekday,
            'empty_days': empty_days,
            'today_nepali': english_to_nepali(timezone.now().date()),
        })
        return context