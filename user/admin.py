from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from user.models import AuthUser, Profile, WorkingDetail, Document, Payout, BankDetail
class AuthUserAdmin(UserAdmin):
    fieldsets = (
        (None, {
            "fields": (
                "middle_name",
            ),
        }),
    )
    
# class ProfileAdmin()

# Register your models here.
admin.site.register([AuthUser,Profile, WorkingDetail, Document, Payout,BankDetail])
