from __future__ import annotations

from django.urls import path

from . import views

app_name = "auth_app"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("login/submit/", views.login_submit, name="login_submit"),
    path("logout/", views.logout_view, name="logout"),
    path("auth/callback/", views.auth_callback, name="auth_callback"),
    path("auth/callback/process/", views.auth_callback_process, name="auth_callback_process"),
]
