from django import forms
import datetime
from datetime import timedelta
from branch.models import Branch
from department.models import Department
from fiscal_year.models import FiscalYear
from utils.date_converter import english_to_nepali, nepali_str_to_english
from .models import EmployeeLeave, Leave, LeaveType
from django.core.exceptions import ValidationError
from nepali_datetime import date as nep_date


#Leave Type
class LeaveTypeForm(forms.ModelForm):
    class Meta:
        model = LeaveType
        fields = (
            'fiscal_year', 'name', 'code', 'number_of_days', 'leave_type', 'gender', 'marital_status',
            'description', 'show_on_employee',
            'prorata_status', 'encashable_status', 'half_leave_status',
            'half_leave_type', 'carry_forward_status', 'sandwich_rule_status',
            'pre_inform_days', 'max_per_day_leave', 'status', 'job_type',
            'branches', 'departments',
        )
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Enter title'}),
            'code': forms.TextInput(attrs={'placeholder': 'Enter code'}),
            'number_of_days': forms.NumberInput(attrs={'placeholder': 'Enter number of days'}),
            'description': forms.Textarea(attrs={'placeholder': 'Write description here...'}),
            'pre_inform_days': forms.NumberInput(attrs={'placeholder': 'e.g. 3'}),
            'max_per_day_leave': forms.NumberInput(attrs={'placeholder': 'e.g. 2'}),
            'branches': forms.SelectMultiple(attrs={
                'class': 'form-control select2-multiple',
                'data-placeholder': 'Select Branches',
                'multiple': 'multiple'
            }),
            'departments': forms.SelectMultiple(attrs={
                'class': 'form-control select2-multiple',
                'data-placeholder': 'Select Departments',
                'multiple': 'multiple'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['fiscal_year'].empty_label = "Select Fiscal Year"
        self.fields['fiscal_year'].queryset = FiscalYear.objects.filter(status='active').order_by('-id')

        self.fields['branches'].queryset = Branch.objects.all()
        self.fields['departments'].queryset = Department.objects.all()

        # Only apply default if creating a new LeaveType (not editing)
        if not self.instance.pk:
            try:
                current_fy = FiscalYear.current_fiscal_year()
                if current_fy:
                    self.initial['fiscal_year'] = current_fy.id
            except FiscalYear.DoesNotExist:
                pass


#Leave
class LeaveForm(forms.ModelForm):
    start_date = forms.CharField(widget=forms.TextInput(attrs={
        'placeholder': 'YYYY-MM-DD (BS)', 'class': 'nep_date'
    }))
    end_date = forms.CharField(widget=forms.TextInput(attrs={
        'placeholder': 'YYYY-MM-DD (BS)', 'class': 'nep_date'
    }))
    class Meta:
        model = Leave
        fields = (
            'leave_type', 'start_date', 'end_date', 'reason'
        )
        widgets = {
            'reason': forms.Textarea(attrs={'placeholder': 'Write reason here...'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)  # Get user from kwargs
        super().__init__(*args, **kwargs)
        self.fields['leave_type'].empty_label = "Select Leave Type"

        if self.user:
            assigned_leave_type_ids = EmployeeLeave.objects.filter(
                is_active=True,
                employee=self.user,
                leave_type__fiscal_year__is_current=True,
            ).values_list('leave_type_id', flat=True)

            self.fields['leave_type'].queryset = LeaveType.objects.filter(id__in=assigned_leave_type_ids)

        #Convert instance English dates to Nepali for display in the form
        if self.instance and self.instance.pk:
            if self.instance.start_date:
                self.initial['start_date'] = english_to_nepali(self.instance.start_date)
            if self.instance.end_date:
                self.initial['end_date'] = english_to_nepali(self.instance.end_date)

    def clean(self):
        cleaned_data = super().clean()
        leave_type = cleaned_data.get('leave_type')

        start_date_nep_str = cleaned_data.get('start_date')
        end_date_nep_str = cleaned_data.get('end_date')

         # Convert to English date
        try:
            cleaned_data['start_date'] = nepali_str_to_english(start_date_nep_str)
        except Exception:
            self.add_error('start_date', "Invalid Nepali date format or non-existent date.")

        try:
            cleaned_data['end_date'] = nepali_str_to_english(end_date_nep_str)
        except Exception:
            self.add_error('end_date', "Invalid Nepali date format or non-existent date.")

        # Check if start date is greater than end date
        if cleaned_data['end_date'] < cleaned_data['start_date']:
            raise ValidationError("End date cannot be before start date.")

        cleaned_data['no_of_days'] = (cleaned_data['end_date'] - cleaned_data['start_date']).days + 1

        if leave_type:
            #max_per_day_leave check
            if leave_type.max_per_day_leave and cleaned_data['no_of_days'] > leave_type.max_per_day_leave:
                raise ValidationError(
                    f"You cannot take more than {leave_type.max_per_day_leave} days for this leave type."
                )

            #pre_inform_days check
            if leave_type.pre_inform_days:
                today = datetime.date.today()
                days_in_advance = (cleaned_data['start_date'] - today).days
                if abs(days_in_advance) < leave_type.pre_inform_days:
                    raise ValidationError(
                        f"You must apply at least {leave_type.pre_inform_days} day(s) in advance."
                    )

        #Check for overlapping leaves with specific dates
        overlapping_leaves = Leave.objects.filter(
            employee=self.user,
            start_date__lte=cleaned_data['end_date'],
            end_date__gte=cleaned_data['start_date'],
        ).exclude(status__in=['Declined', 'Rejected'])

        # Exclude current instance when editing
        if self.instance and self.instance.pk:            
            overlapping_leaves = overlapping_leaves.exclude(pk=self.instance.pk)

        if overlapping_leaves.exists():
            # Create set of requested English dates
            requested_dates = set(cleaned_data['start_date'] + timedelta(days=i) for i in range(cleaned_data['no_of_days']))
            taken_dates = set()

            for leave in overlapping_leaves:
                leave_dates = set(
                    leave.start_date + timedelta(days=i)
                    for i in range((leave.end_date - leave.start_date).days + 1)
                )
                taken_dates |= leave_dates

            conflict_dates = sorted(requested_dates & taken_dates)

            if conflict_dates:
                roster_conflict_dates = []
                general_conflict_dates = []

                for date in conflict_dates:
                    overlapping_on_day = overlapping_leaves.filter(
                        start_date__lte=date, end_date__gte=date
                    )
                    is_roster = any(overlap.leave_type.code == 'weekly' for overlap in overlapping_on_day)

                    if is_roster:
                        roster_conflict_dates.append(date)
                    else:
                        general_conflict_dates.append(date)

                error_messages = []

                if roster_conflict_dates:
                    formatted_roster_dates = ', '.join([
                        english_to_nepali(date).strftime('%Y-%m-%d')
                        for date in sorted(set(roster_conflict_dates))
                    ])
                    error_messages.append(f"Roster Leave is on: {formatted_roster_dates}.")

                if general_conflict_dates:
                    formatted_general_dates = ', '.join([
                        english_to_nepali(date).strftime('%Y-%m-%d')
                        for date in sorted(set(general_conflict_dates))
                    ])
                    error_messages.append(f"You have already taken leave on: {formatted_general_dates}.")

                if error_messages:
                    raise ValidationError('\n'.join(error_messages))
            
        return cleaned_data
