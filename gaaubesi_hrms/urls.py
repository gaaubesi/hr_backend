from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from .views import DashboardView, LoginUserView, UserLogoutView

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', DashboardView.as_view(), name='dashboard'),
    path('login/', LoginUserView.as_view(), name='login'),
    path('logout/', UserLogoutView.as_view(), name='logout'),

    path('employee/', include("user.urls")),
    path('roster/', include("roster.urls")),

    path("leave/", include("leave.urls")),
    path("attendance/", include("attendance.urls")),
    path("fiscal-year/", include("fiscal_year.urls")),

    path('departments/', include('department.urls', namespace='department')),
    path('branch/', include('branch.urls', namespace='branch')),
    path('payout/', include('payout.urls', namespace='payout')),
    path('setup/', include('setup.urls', namespace='setup')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

