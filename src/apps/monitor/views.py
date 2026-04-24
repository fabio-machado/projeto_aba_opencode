from django.http import HttpRequest, HttpResponse
from django.template.response import TemplateResponse


def monitor_view(request: HttpRequest) -> HttpResponse:
    """Placeholder view for monitor/reports section."""
    return TemplateResponse(request, "monitor/monitor.html")


def monitor_create_view(request: HttpRequest) -> HttpResponse:
    """Placeholder view for creating monitor content."""
    return TemplateResponse(request, "monitor/monitor_create.html")
