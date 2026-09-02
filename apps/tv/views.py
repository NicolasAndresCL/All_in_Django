"""Endpoint del módulo TV Chile (solo lectura)."""

from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from core.openapi import PARAM_BUSCAR, CanalesSerializer, ErrorDominioSerializer

from .services import obtener_canales


class CanalesTVView(APIView):
    """GET /api/tv/canales/?buscar=<texto> — lista de canales (cacheada)."""

    # APIView sin serializer: spectacular no puede deducir nada, hay que declararlo todo.
    # El 502 no es teorico: la fuente es una web ajena y `ScraperError` se mapea ahi.
    @extend_schema(
        summary="Lista los canales de TV chilena (scraping cacheado 1 h)",
        parameters=[PARAM_BUSCAR],
        responses={200: CanalesSerializer, 502: ErrorDominioSerializer},
    )
    def get(self, request):
        canales = obtener_canales()
        buscar = request.query_params.get("buscar")
        if buscar:
            canales = [c for c in canales if buscar.lower() in c["name"].lower()]
        return Response({"total": len(canales), "canales": canales})
