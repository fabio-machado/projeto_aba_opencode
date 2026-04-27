"""
Views for the core app.

Views only validate input, call services, and return responses.
No business logic should be implemented here.
"""

from django.http import HttpRequest, HttpResponse
from django.template.response import TemplateResponse


def index_view(request: HttpRequest) -> HttpResponse:
    """
    Index view — renders the home page.
    """
    return TemplateResponse(request, "home.html")


def health_view(request: HttpRequest) -> HttpResponse:
    """
    Health check endpoint for Docker and monitoring.

    Returns HTTP 200 with simple JSON response.
    """
    from django.http import JsonResponse

    return JsonResponse({"status": "healthy"})
