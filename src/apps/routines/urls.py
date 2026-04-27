from django.urls import path

from . import views

app_name = "routines"

urlpatterns = [
    path("", views.routines_view, name="routines"),
    path("create/", views.routines_create_view, name="routines_create"),
]
