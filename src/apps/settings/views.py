from django.http import HttpRequest, HttpResponse
from django.template.response import TemplateResponse


def settings_view(request: HttpRequest) -> HttpResponse:
    """Placeholder view for settings section."""
    return TemplateResponse(request, "settings/settings.html")


def settings_create_view(request: HttpRequest) -> HttpResponse:
    """Placeholder view for creating settings content."""
    return TemplateResponse(request, "settings/settings_create.html")
