"""
ASGI config for Autismo em Foco project.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prd")

application = get_asgi_application()
