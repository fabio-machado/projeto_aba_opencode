"""
WSGI config for Autismo em Foco project.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prd")

application = get_wsgi_application()
