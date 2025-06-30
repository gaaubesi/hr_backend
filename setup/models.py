from django.db import models

# Create your models here.

class Setup(models.Model):
    CALENDAR_CHOICES = [
        ('ad', 'AD'),
        ('bs', 'BS'),
    ]
    
    calendar_type = models.CharField(
        max_length=2,
        choices=CALENDAR_CHOICES,
        default='ad',
        verbose_name='Calendar Type'
    )
    shift_threshold = models.IntegerField(
        verbose_name='Shift Threshold (minutes)',
        help_text='Threshold in minutes for shift calculations'
    )
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    @classmethod
    def get_calendar_type(cls):
        setup = cls.objects.first()
        return setup.calendar_type if setup else 'bs'

    def __str__(self):
        return f"{self.get_calendar_type_display()} - {self.shift_threshold} minutes"

    class Meta:
        verbose_name = 'Setup'
        verbose_name_plural = 'Setups'
        ordering = ['-created_on']