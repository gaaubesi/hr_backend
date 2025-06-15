from django import forms

from utils.date_converter import english_to_nepali, nepali_str_to_english
from .models import Profile, WorkingDetail
from .models import AuthUser
from django.core.exceptions import ValidationError

class UserForm(forms.ModelForm):
    class Meta:
        model = AuthUser
        fields = ('username', 'first_name', 'middle_name', 'last_name', 'email')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].required = True
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['email'].required = True

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if AuthUser.objects.filter(username=username).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise ValidationError("This username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if AuthUser.objects.filter(email=email).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise ValidationError("This email is already registered.")
        return email

class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ('dob', 'gender', 'marital_status', 'address', 'mobile_number', 'personal_email', 'religion', 'blood_group')
        widgets = {
            'dob': forms.DateInput(attrs={'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['gender'].choices = [
            choice for choice in self.fields['gender'].choices if choice[0] != 'A'
        ]

        self.fields['marital_status'].choices = [
            choice for choice in self.fields['marital_status'].choices if choice[0] != 'A'
        ]

        self.fields['religion'].choices = [
            choice for choice in self.fields['religion'].choices if choice[0] != 'A'
        ]

        self.fields['mobile_number'].required = True

    def clean_mobile_number(self):
        mobile_number = self.cleaned_data.get('mobile_number')
        if Profile.objects.filter(mobile_number=mobile_number).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise ValidationError("This mobile number is already registered.")
        return mobile_number

    def clean_personal_email(self):
        personal_email = self.cleaned_data.get('personal_email')
        if personal_email and Profile.objects.filter(personal_email=personal_email).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise ValidationError("This personal email is already registered.")
        return personal_email

class WorkingDetailForm(forms.ModelForm):
    # Override joining_date as CharField to avoid early parsing
    joining_date = forms.CharField(widget=forms.TextInput(attrs={
        'placeholder': 'YYYY-MM-DD (BS)', 'id': 'joining_date'
    }))
    
    class Meta:
        model = WorkingDetail
        fields = ('shift', 'job_type', 'joining_date', 'department')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['job_type'].choices = [
            choice for choice in self.fields['job_type'].choices if choice[0] != 'all'
        ]
        if self.instance and self.instance.pk:
            if self.instance.joining_date:
                self.initial['joining_date'] = english_to_nepali(self.instance.joining_date)

    
    def clean(self):
        cleaned_data = super().clean()
        joining_date_str = cleaned_data.get('joining_date')

        # Convert to English date
        try:
            cleaned_data['joining_date'] = nepali_str_to_english(joining_date_str)
        except Exception:
            self.add_error('joining_date', "Invalid Nepali date format or non-existent date.")

        return cleaned_data
