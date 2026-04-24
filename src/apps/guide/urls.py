from django.urls import path

from . import views

app_name = "guide"

urlpatterns = [
    path("", views.guide_view, name="guide"),
    path("create/", views.guide_create_view, name="guide_create"),
]
