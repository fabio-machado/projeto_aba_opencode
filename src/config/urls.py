"""
Root URL configuration for Autismo em Foco project.
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.core.urls")),
    path("routines/", include("apps.routines.urls")),
    path("guide/", include("apps.guide.urls")),
    path("monitor/", include("apps.monitor.urls")),
    path("settings/", include("apps.settings.urls")),
    path("", include("apps.payments.urls")),
]
