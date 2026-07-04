"""Endpoint del módulo TV Chile (solo lectura)."""

from rest_framework.response import Response
from rest_framework.views import APIView

from .services import obtener_canales


class CanalesTVView(APIView):
    """GET /api/tv/canales/?buscar=<texto> — lista de canales (cacheada)."""

    def get(self, request):
        canales = obtener_canales()
        buscar = request.query_params.get("buscar")
        if buscar:
            canales = [c for c in canales if buscar.lower() in c["name"].lower()]
        return Response({"total": len(canales), "canales": canales})
