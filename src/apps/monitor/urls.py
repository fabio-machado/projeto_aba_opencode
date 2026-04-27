from django.urls import path

from . import views

app_name = "monitor"

urlpatterns = [
    path("", views.monitor_view, name="monitor"),
    path("create/", views.monitor_create_view, name="monitor_create"),
]
