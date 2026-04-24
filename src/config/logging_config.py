"""
Logging configuration for Autismo em Foco project.

Uses structlog for structured logging with:
- JSON formatter for production
- Colored console formatter for development
"""

import sys
from typing import Any, Dict

import structlog


def get_logging_config(log_level: str = "INFO", environment: str = "dev") -> Dict[str, Any]:
    """
    Generate Django LOGGING configuration dict.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        environment: Environment name ('dev' or 'prd')

    Returns:
        Dictionary compatible with Django LOGGING setting
    """
    is_production = environment.lower() in ("prd", "production", "prod")

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer() if is_production else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "fmt": "%(asctime)s %(name)s %(levelname)s %(message)s",
            },
            "console": {
                "()": "colorlog.ColoredFormatter",
                "fmt": "%(log_color)s%(asctime)s %(name)s %(levelname)s %(message)s",
                "log_colors": {
                    "DEBUG": "cyan",
                    "INFO": "green",
                    "WARNING": "yellow",
                    "ERROR": "red",
                    "CRITICAL": "red,bg_white",
                },
            },
        },
        "handlers": {
            "console": {
                "level": log_level,
                "class": "logging.StreamHandler",
                "stream": sys.stdout,
                "formatter": "console" if not is_production else "json",
            },
        },
        "loggers": {
            "": {
                "handlers": ["console"],
                "level": log_level,
                "propagate": False,
            },
            "django": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False,
            },
        },
    }
