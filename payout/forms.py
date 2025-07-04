import datetime
from django import forms
import nepali_datetime
from fiscal_year.models import FiscalYear
from payout.models import SalaryRelease, SalaryType
from user.models import AuthUser
from utils.date_converter import english_to_nepali, nepali_str_to_english
from .models import PayoutInterval

class SalaryTypeForm(forms.ModelForm):
    class Meta:
        model = SalaryType
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'})
        }
    def __init__(self, *args, **kwargs):
        super(SalaryTypeForm,self).__init__(*args, **kwargs)
        self.fields['name'].required = True


class SalaryReleaseForm(forms.ModelForm):
    start_date = forms.CharField(widget=forms.TextInput(attrs={
        'placeholder': 'YYYY-MM-DD (BS)', 'class': 'nep_date readonly-input'
    }))
    end_date = forms.CharField(widget=forms.TextInput(attrs={
        'placeholder': 'YYYY-MM-DD (BS)', 'class': 'nep_date readonly-input'
    }))
    class Meta:
        model = SalaryRelease
        fields = ['employee', 'salary_type', 'start_date', 'end_date', 'fiscal_year', 'month', 'amount', 'no_of_product', 'rate', 'tax', 'net_amount']

    def __init__(self, *args, **kwargs):
        super(SalaryReleaseForm, self).__init__(*args, **kwargs)
        self.fields['employee'].queryset = AuthUser.get_active_users()
        self.fields['fiscal_year'].queryset = FiscalYear.active_fiscal_year_list()
        
        self.fields['employee'].empty_label = "Select Team Member"
        self.fields['salary_type'].empty_label = "Select Salary Type"
        self.fields['fiscal_year'].empty_label = "Select Fiscal Year"

        # Only for new instances
        if not self.instance.pk:
            current_fy = FiscalYear.current_fiscal_year()
            if current_fy:
                self.initial['fiscal_year'] = current_fy.pk

                # Get current Nepali month
                nepali_date_str = nepali_datetime.date.today().strftime('%Y-%m-%d')
                current_month = int(nepali_date_str.split('-')[1])
                # current_month = 3

                self.initial['month'] = current_month

                # Find English dates within current Nepali month
                nepali_range = []
                eng_date = current_fy.start_date
                while eng_date <= current_fy.end_date:
                    nep = english_to_nepali(eng_date).strftime('%Y-%m-%d')
                    _, month, _ = map(int, nep.split('-'))
                    if month == current_month:
                        nepali_range.append(eng_date)
                    eng_date += datetime.timedelta(days=1)

                if nepali_range:
                    self.initial['start_date'] = english_to_nepali(nepali_range[0])
                    self.initial['end_date'] = english_to_nepali(nepali_range[-1])


        # For edit form: show existing start/end dates in Nepali
        if self.instance and self.instance.pk:
            if self.instance.start_date:
                self.initial['start_date'] = english_to_nepali(self.instance.start_date)
            if self.instance.end_date:
                self.initial['end_date'] = english_to_nepali(self.instance.end_date)

    def clean(self):
        cleaned_data = super(SalaryReleaseForm, self).clean()
        
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
        
        return cleaned_data

class PayoutIntervalForm(forms.ModelForm):
    class Meta:
        model = PayoutInterval
        fields = ['name', 'day']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'day': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    