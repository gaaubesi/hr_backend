from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from decimal import Decimal

from djgeojson.fields import PointField

# Create your models here.
class Attendance(models.Model):
    employee = models.ForeignKey('user.AuthUser', on_delete=models.CASCADE, related_name='attendance')
    date = models.DateField(default=timezone.now)
    actual_checkin_time = models.TimeField(null=True, blank=True)
    actual_checkout_time = models.TimeField(null=True, blank=True)
    checkin_time = models.TimeField(null=True, blank=True)
    checkout_time = models.TimeField(null=True, blank=True)
    working_hours = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))], null=True, blank=True)
    checkin_location = PointField(null=True, blank=True)
    checkout_location = PointField(null=True, blank=True)
    checkin_devices = models.CharField(max_length=100, null=True, blank=True)
    checkout_devices = models.CharField(max_length=100, null=True, blank=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    shift = models.ForeignKey('roster.Shift', on_delete=models.CASCADE, related_name='attendance', null=True, blank=True)

    def __str__(self):
        return f"{self.date}"

class RequestStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    FORWARDED = 'forwarded', 'Forwarded'
    APPROVED = 'approved', 'Approved'
    REJECTED = 'rejected', 'Rejected'
    CANCELLED = 'cancelled', 'Cancelled'

class RequestType(models.TextChoices):
    MISSED_CHECKOUT = 'missed_checkout', 'Missed Checkout'
    LATE_ARRIVAL_REQUEST = 'late_arrival_request', 'Late Arrival Request'
    EARLY_DEPARTURE_REQUEST = 'early_departure_request', 'Early Departure Request'
    
class Request(models.Model):
    employee = models.ForeignKey('user.AuthUser', on_delete=models.CASCADE, related_name='attendance_requests')
    type = models.CharField(max_length=50, choices=RequestType.choices)
    date = models.DateField(default=timezone.now)
    time = models.TimeField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=RequestStatus.choices, default=RequestStatus.PENDING)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.type} - {self.employee.username}"
    