from django.urls import path

from . import views

app_name = "settings"

urlpatterns = [
    path("", views.settings_view, name="settings"),
    path("create/", views.settings_create_view, name="settings_create"),
]
