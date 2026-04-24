from django.http import HttpRequest, HttpResponse
from django.template.response import TemplateResponse


def guide_view(request: HttpRequest) -> HttpResponse:
    """Placeholder view for ABA guide section."""
    return TemplateResponse(request, "guide/guide.html")


def guide_create_view(request: HttpRequest) -> HttpResponse:
    """Placeholder view for creating guide content."""
    return TemplateResponse(request, "guide/guide_create.html")
