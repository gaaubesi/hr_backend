from datetime import datetime, timedelta
from django.db import models
from roster.models import Shift

class Setup(models.Model):
    CALENDAR_CHOICES = [
        ('bs', 'BS'),
        ('ad', 'AD'),
    ]

    calendar_type = models.CharField(
        max_length=2,
        choices=CALENDAR_CHOICES,
        default='bs',
        verbose_name='Calendar Type'
    )
    shift_threshold = models.IntegerField(
        verbose_name='Shift Threshold (minutes)',
        help_text='Threshold in minutes for shift calculations'
    )
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    _original_shift_threshold = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_shift_threshold = self.shift_threshold

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)

        # Always update shifts if it's a new Setup
        if is_new or self.shift_threshold != self._original_shift_threshold:
            threshold_delta = timedelta(minutes=self.shift_threshold)

            for shift in Shift.objects.all():
                base_date = datetime(2000, 1, 1)  # base date to do time arithmetic
                min_time = (datetime.combine(base_date, shift.start_time) - threshold_delta).time()
                max_time = (datetime.combine(base_date, shift.end_time) + threshold_delta).time()

                shift.min_start_time = min_time
                shift.max_end_time = max_time
                shift.save()

        self._original_shift_threshold = self.shift_threshold

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
