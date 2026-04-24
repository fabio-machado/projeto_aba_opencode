"""
Views for the core app.

Views only validate input, call services, and return responses.
No business logic should be implemented here.
"""

import uuid
from typing import Union

from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.template.response import TemplateResponse

from .services import ExampleService


def index_view(request: HttpRequest) -> HttpResponse:
    """
    Index view demonstrating the View Response Pattern.

    Rules:
    1. Validate input
    2. Call service
    3. Return response (partial for HTMX, full page otherwise)
    """
    service = ExampleService()
    user_id = uuid.uuid4()

    try:
        result = service.get_example_data(user_id=user_id)
    except ValueError as e:
        return HttpResponseBadRequest(str(e))

    if request.headers.get("HX-Request"):
        return TemplateResponse(
            request,
            "core/partials/_example_partial.html",
            {"result": result},
        )

    return TemplateResponse(
        request,
        "base.html",
        {"result": result},
    )


def health_view(request: HttpRequest) -> HttpResponse:
    """
    Health check endpoint for Docker and monitoring.

    Returns HTTP 200 with simple JSON response.
    """
    from django.http import JsonResponse

    return JsonResponse({"status": "healthy"})
