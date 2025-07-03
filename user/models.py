from django.db import models
from django.utils import timezone

from django.contrib.auth.models import AbstractUser
from nepali_datetime_field.models import NepaliDateField

from leave.models import JobType
from utils.enums import GENDER
from utils.enums import MARITAL_STATUS
from utils.enums import RELIGION


# Create your models here.
class AuthUser(AbstractUser):
    middle_name = models.CharField(max_length=150, blank=True)

    first_name = models.CharField(max_length=150, blank=False)
    last_name = models.CharField(max_length=150, blank=False)
    username = models.CharField(max_length=150, unique=True, blank=False)
    email = models.EmailField(verbose_name='Official email', unique=True, blank=False)

    def full_name(self):
        parts = [self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        parts.append(self.last_name)
        return ' '.join(part for part in parts if part)
    
    @property
    def attendance_status_button(self):
        todays_attendance = self.attendance.filter(
            # date=timezone.localdate()
            date=timezone.now()
        )
        if todays_attendance.exists():
            # if todays_attendance.first().status == "CheckedOut":
            #     return "Already CheckedIn"
            # elif todays_attendance.first().status == "PaidLeave" or todays_attendance.first().status == "UnpaidLeave":
            #     return "Leave"
            # elif todays_attendance.first().status == "RoasterLeave":
            #     return "Roaster Leave"
            # else:
            #     return "CheckOut"

            if todays_attendance.first().checkin_time and not todays_attendance.first().checkout_time:
                return "CheckOut"
            elif todays_attendance.first().checkout_time:
                return "Already CheckedOut"
        else:
            return "CheckIn"  
    
    @classmethod
    def get_active_users(cls):
        return cls.objects.filter(is_active=True, is_superuser=False).order_by('first_name')
    
    def __str__(self):
        return self.username

class Profile(models.Model):
    BLOOD_GROUPS = [
        ('A+', 'A+'),
        ('A-', 'A-'),
        ('B+', 'B+'),
        ('B-', 'B-'),
        ('O+', 'O+'),
        ('O-', 'O-'),
        ('AB+', 'AB+'),
        ('AB-', 'AB-'),
    ]
    

    user = models.OneToOneField(AuthUser, related_name='profile', on_delete=models.CASCADE)
    profile_picture = models.ImageField(upload_to='profile_pictures/', null=True, blank=True)
    address = models.CharField(max_length=100, blank=True, null=True)
    dob = models.DateField(null=True, verbose_name='Date of birth')
    gender = models.CharField(max_length=1, choices=GENDER, default='F')
    religion = models.CharField(max_length=50, choices=RELIGION, default='H')
    mobile_number = models.CharField(max_length=15, blank=True, null=True)      
    secondary_number = models.CharField(max_length=15, blank=True, null=True)      
    personal_email = models.EmailField(blank=True, null=True, verbose_name='Personal email')
    blood_group = models.CharField(max_length=5, choices=BLOOD_GROUPS, null=True, blank=True)
    marital_status = models.CharField(max_length=1, choices=MARITAL_STATUS, default="S")
    is_verified = models.BooleanField(default=False)
    currently_working = models.BooleanField(default=True)


class WorkingDetail(models.Model):
    employee = models.OneToOneField(AuthUser, related_name='working_detail', on_delete=models.CASCADE)
    shift = models.ForeignKey('roster.Shift', related_name='shift', on_delete=models.SET_NULL, null=True)
    job_type = models.CharField(choices=JobType.choices, default=JobType.PROBATION, verbose_name="Job Type")
    joining_date = models.DateField(null=True, verbose_name="Joining Date")
    department = models.ForeignKey('department.Department', related_name='department', on_delete=models.SET_NULL, null=True)
    branch = models.ForeignKey('branch.Branch', related_name='branch', on_delete=models.SET_NULL, null=True, verbose_name="Substation")


class Document(models.Model):
    DOCUMENT_TYPES = [
        ('citizenship_front', 'Citizenship Front'),
        ('citizenship_back', 'Citizenship Back'),
        ('pan_card', 'PAN Card'),
        ('resume', 'Resume'),
        ('other', 'Other'),
    ]

    user = models.ForeignKey(AuthUser, related_name='documents', on_delete=models.CASCADE)
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPES)
    document_file = models.FileField(null=True, upload_to='documents/', blank=True)
    document_number = models.CharField(max_length=50, null=True, blank=True, verbose_name='Document Number')
    issue_body = models.ForeignKey('branch.District', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Issuing Authority')
    issue_date = models.DateField(null=True, verbose_name="Issue Date")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Document'
        verbose_name_plural = 'Documents'
        
    def __str__(self):  
        return f"{self.user.username} - {self.get_document_type_display()}"


class Payout(models.Model):
    user = models.ForeignKey(AuthUser, related_name='payouts', on_delete=models.CASCADE)
    payout_interval = models.ForeignKey('payout.PayoutInterval', related_name='payouts', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    assign_overtime  = models.BooleanField(default=False)
    created_on = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Payout'
        verbose_name_plural = 'Payouts'
        ordering = ['-created_on']
        
    def __str__(self):
        return f"{self.user.username} - {self.payout_interval.name} - {self.amount}"


class BankDetail(models.Model):
    account_holder = models.ForeignKey(
        AuthUser, on_delete=models.CASCADE, related_name='bank_details', blank=True)
    bank_name = models.CharField(max_length=50)
    bank_username = models.CharField(max_length=50, null=True)
    branch = models.CharField(max_length=20)
    account_number = models.BigIntegerField()
    is_primary = models.BooleanField(null=True, blank=True)

    def __str__(self):
        return f"{self.bank_name} - {self.account_number} ({self.account_holder.username})"

    