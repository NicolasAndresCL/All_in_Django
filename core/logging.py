"""
core/logging.py — Configuración de logging centralizada.

`construir_logging()` arma el dict de `LOGGING` que consume `config/settings.py`, y
`get_logger` es el helper que usan los servicios para registrar eventos y errores.

**Dos formatos, un solo cableado** (`LOG_FORMATO` en `core.conf`):

- `texto` — el de siempre, para leerlo en la consola durante el desarrollo.
- `json` — una línea JSON por registro, para los contenedores. Un agregador puede
  filtrar por `level`, `logger` o `status_code` sin adivinar con expresiones
  regulares sobre texto libre, que es lo que hace falta para vigilar de verdad.

El formato NO se deriva de `DEBUG`: igual que `SECURE_HTTPS`, es un toggle explícito.
Un despliegue puede querer `DEBUG=False` y logs legibles mientras se depura.

Trampa ya pagada: la ruta de importación del formateador es
`pythonjsonlogger.json.JsonFormatter`. La antigua `pythonjsonlogger.jsonlogger`
sigue funcionando pero emite un DeprecationWarning.
"""

import logging

# Campos que se incluyen en cada línea JSON. `fmt` no imprime nada aquí: le dice al
# formateador QUÉ atributos del LogRecord serializar.
_CAMPOS_JSON = "%(asctime)s %(levelname)s %(name)s %(message)s %(module)s %(funcName)s %(lineno)d"


def construir_logging(formato: str = "texto", nivel: str = "INFO") -> dict:
    """Config de logging (`dictConfig`) para el formato y nivel pedidos."""
    nivel = nivel.upper()
    handler = "json" if formato == "json" else "console"

    return {
        "version": 1,
        # False: los loggers de Django y de terceros que ya existan siguen vivos.
        "disable_existing_loggers": False,
        "formatters": {
            "verbose": {
                "format": "[{asctime}] {levelname} {name}: {message}",
                "style": "{",
            },
            "json": {
                "()": "pythonjsonlogger.json.JsonFormatter",
                "fmt": _CAMPOS_JSON,
                # `levelname` -> `level` y `asctime` -> `timestamp`: los nombres que
                # esperan los agregadores habituales (Loki, ELK).
                "rename_fields": {"levelname": "level", "asctime": "timestamp"},
                # Identifica el servicio cuando varios escriben al mismo sitio.
                "static_fields": {"service": "all-in-django"},
            },
        },
        "handlers": {
            "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
            "json": {"class": "logging.StreamHandler", "formatter": "json"},
        },
        "root": {"handlers": [handler], "level": nivel},
        "loggers": {
            "apps": {"handlers": [handler], "level": nivel, "propagate": False},
            "core": {"handlers": [handler], "level": nivel, "propagate": False},
            # django.request registra los 4xx/5xx que sirve la app. Sin él, un 500 solo
            # se ve en el traceback de gunicorn y no queda como evento estructurado.
            "django.request": {"handlers": [handler], "level": "WARNING", "propagate": False},
        },
    }


# Config por defecto (formato texto). `config/settings.py` la reconstruye con los
# valores de `core.conf`; esta constante mantiene compatible cualquier import previo.
LOGGING = construir_logging()


def get_logger(name: str) -> logging.Logger:
    """Devuelve un logger con nombre (normalmente `__name__`)."""
    return logging.getLogger(name)
