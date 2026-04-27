"""
Production settings for Autismo em Foco project.
"""

import os

from .base import *  # noqa: F401, F403

DEBUG = False
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Security settings
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True

# Allowed hosts must be set in production
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "").split(",")

# Validate required environment variables in production
_REQUIRED_ENV_VARS = ["SUPABASE_URL", "SUPABASE_KEY", "SECRET_KEY"]
for var in _REQUIRED_ENV_VARS:
    if not os.getenv(var):
        raise ValueError(
            f"Missing required environment variable: {var}. "
            f"Production deployment requires all critical env vars to be set."
        )
