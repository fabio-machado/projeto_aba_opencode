"""
URL configuration for the core app.
"""

from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.index_view, name="index"),
    path("health/", views.health_view, name="health"),
]
