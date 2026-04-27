from django.http import HttpRequest, HttpResponse
from django.template.response import TemplateResponse


def routines_view(request: HttpRequest) -> HttpResponse:
    """Placeholder view for routines section."""
    return TemplateResponse(request, "routines/routines.html")


def routines_create_view(request: HttpRequest) -> HttpResponse:
    """Placeholder view for creating routines."""
    return TemplateResponse(request, "routines/routines_create.html")
