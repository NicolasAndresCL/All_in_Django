"""
core/exceptions.py — Excepciones de dominio claras + handler DRF.

Las excepciones de negocio heredan de `AllInDjangoError`. `custom_exception_handler`
las traduce a respuestas JSON con código HTTP adecuado, en vez de un 500 opaco.
Se registra en REST_FRAMEWORK["EXCEPTION_HANDLER"].
"""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_default_handler

from core.logging import get_logger

logger = get_logger(__name__)


class AllInDjangoError(Exception):
    """Excepción base de la aplicación."""


class ArchivoInvalidoError(AllInDjangoError):
    """El archivo subido no se puede leer o le faltan columnas requeridas."""


class ImportacionError(AllInDjangoError):
    """Fallo al transformar/guardar datos importados."""


class ScraperError(AllInDjangoError):
    """Fallo al obtener datos externos (p. ej. el scraper de TV)."""


# Mapa excepción → código HTTP (dispatch table en vez de if/elif anidados).
_HTTP_POR_EXCEPCION = {
    ArchivoInvalidoError: status.HTTP_400_BAD_REQUEST,
    ImportacionError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    ScraperError: status.HTTP_502_BAD_GATEWAY,
}


def custom_exception_handler(exc, context):
    """Handler de DRF: primero el por defecto; si no aplica, mapea las de dominio."""
    respuesta = drf_default_handler(exc, context)
    if respuesta is not None:
        return respuesta

    for tipo, codigo in _HTTP_POR_EXCEPCION.items():
        if isinstance(exc, tipo):
            logger.warning("%s: %s", tipo.__name__, exc)
            return Response({"error": str(exc), "tipo": tipo.__name__}, status=codigo)

    logger.exception("Error no controlado", exc_info=exc)
    return None  # deja que Django produzca el 500 estándar
