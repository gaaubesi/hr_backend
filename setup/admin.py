from django.contrib import admin
from .models import Setup

@admin.register(Setup)
class SetupAdmin(admin.ModelAdmin):
    list_display = ('calendar_type', 'shift_threshold', 'created_on', 'updated_on')
    list_filter = ('calendar_type', 'created_on')
    search_fields = ('calendar_type',)
    readonly_fields = ('created_on', 'updated_on')
    ordering = ('-created_on',)
