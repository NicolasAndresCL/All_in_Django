"""
core/logging.py — Configuración de logging centralizada.

`LOGGING` se inyecta en `config/settings.py`. `get_logger` es el helper que usan
los servicios para registrar eventos y errores (try/except + logger).
"""

import logging

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "apps": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "core": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}


def get_logger(name: str) -> logging.Logger:
    """Devuelve un logger con nombre (normalmente `__name__`)."""
    return logging.getLogger(name)
