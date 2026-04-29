"""
Base Django settings for Autismo em Foco project.

Shared settings used by both dev and prd environments.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_htmx",
    "apps.core",
    "apps.routines",
    "apps.guide",
    "apps.monitor",
    "apps.settings",
    "apps.payments",
    "apps.auth",
    "pwa",
]

PWA_APP_NAME = "Autismo em Foco"
PWA_APP_THEME_COLOR = "#14b8a6"
PWA_APP_BACKGROUND_COLOR = "#f8fafc"
PWA_APP_DISPLAY = "standalone"
PWA_APP_ORIENTATION = "portrait"
PWA_APP_START_URL = "/"
PWA_APP_SCOPE = "/"
PWA_APP_STATUS_BAR_COLOR = "black-translucent"
PWA_APP_ICONS = [
    {"src": "/static/images/pwa/icon-192x192.png", "sizes": "192x192"},
    {"src": "/static/images/pwa/icon-512x512.png", "sizes": "512x512"},
]
PWA_APP_ICONS_APPLE = [
    {"src": "/static/images/pwa/icon-192x192.png", "sizes": "192x192"},
    {"src": "/static/images/pwa/icon-512x512.png", "sizes": "512x512"},
]
PWA_SERVICE_WORKER_PATH = "/app/src/static/js/serviceworker.js"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "apps.auth.middleware.LoginRequiredMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases
# Note: Using Supabase (PostgreSQL) via supabase-py for patient data.
# Django DB is only used for auth/session if needed.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Environment variables
SECRET_KEY = os.getenv("SECRET_KEY", "insecure-default-key-change-in-production")
DEBUG = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")

# Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")  # Legacy alias — prefer SUPABASE_SERVICE_KEY
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")

# Stripe
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

# Logging configuration
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "apps": {
            "handlers": ["console"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
        "httpx": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "httpcore": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "stripe": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}

# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
LOGIN_URL = "/login/"

LOGIN_EXEMPT_URLS = [
    r"^/login/$",
    r"^/login/submit/$",
    r"^/auth/callback/$",
    r"^/auth/callback/process/$",
    r"^/logout/$",
    r"^/health/",
    r"^/webhooks/stripe",
    r"^/admin/",
    r"^/static/",
    r"^/manifest\.json$",
    r"^/manifest\.webmanifest$",
    r"^/serviceworker\.js$",
]
