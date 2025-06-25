from django import forms
from .models import Setup

class SetupForm(forms.ModelForm):
    class Meta:
        model = Setup
        fields = ['calendar_type', 'shift_threshold']
        widgets = {
            'calendar_type': forms.Select(attrs={
                'class': 'form-control',
                'data-placeholder': 'Select Calendar Type'
            }),
            'shift_threshold': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter threshold in minutes',
                'min': '0'
            })
        }

    def clean_shift_threshold(self):
        threshold = self.cleaned_data.get('shift_threshold')
        if threshold is not None and threshold < 0:
            raise forms.ValidationError("Shift threshold cannot be negative.")
        return threshold 