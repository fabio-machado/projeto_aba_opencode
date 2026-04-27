from django.urls import path

from . import views

app_name = "payments"

urlpatterns: list = [
    path("webhooks/stripe", views.stripe_webhook, name="stripe_webhook"),
    path("auth/callback", views.auth_callback, name="auth_callback"),
]
