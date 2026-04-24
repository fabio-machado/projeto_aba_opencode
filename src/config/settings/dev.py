"""
Development settings for Autismo em Foco project.
"""

from .base import *  # noqa: F401, F403

DEBUG = True
LOG_LEVEL = "DEBUG"

# Dev-specific middleware for django-debug-toolbar if added later
MIDDLEWARE += [  # noqa: F405
    "django_htmx.middleware.HtmxMiddleware",
]

# Allow all hosts in development
ALLOWED_HOSTS = ["*"]

# Email backend for development
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
