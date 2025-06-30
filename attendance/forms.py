from datetime import datetime
from django import forms

from setup.models import Setup
from utils.date_converter import english_to_nepali, nepali_str_to_english
from .models import Request

class RequestForm(forms.ModelForm):
    date = forms.CharField()
    class Meta:
        model = Request
        fields = ('type', 'date', 'time', 'reason')
        widgets = {
            'type': forms.Select(choices=[('missed_checkout', 'Missed Checkout'), ('late_arrival_request', 'Late Arrival Request'), ('early_departure_request', 'Early Departure Request')]),
            'time': forms.TimeInput(attrs={'type': 'time'}),
            'reason': forms.Textarea(attrs={'placeholder': 'Write reason here...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if Setup.get_calendar_type() == 'bs':
            self.fields['date'].widget = forms.TextInput(attrs={
                'class': 'form-control nep_date',
                'placeholder': 'YYYY-MM-DD (BS)',
                'autocomplete': 'off'
            })
        else:
            self.fields['date'].widget = forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            })

        if self.instance and self.instance.pk:
            if self.instance.date and Setup.get_calendar_type() == 'bs':
                self.initial['date'] = english_to_nepali(self.instance.date)

    def clean_date(self):
        date = self.cleaned_data.get('date')
        calendar_type = Setup.get_calendar_type()

        if calendar_type == 'bs':
            if date:
                try:
                    return nepali_str_to_english(date.strip())
                except Exception as e:
                    raise forms.ValidationError("Invalid Nepali date.")
            return None
        else:
            try:
                return datetime.strptime(date, "%Y-%m-%d").date() if date else None
            except Exception:
                raise forms.ValidationError("Invalid Gregorian date.")   