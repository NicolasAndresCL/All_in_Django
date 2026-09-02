"""ViewSet del módulo Registro de Tareas (CRUD + resumen + exportar)."""

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.api import ExportMixin
from core.openapi import PARAM_PROYECTO, ResumenTareasSerializer

from .models import Registro
from .serializers import RegistroSerializer
from .services import calcular_resumen


@extend_schema_view(list=extend_schema(parameters=[PARAM_PROYECTO]))
class RegistroViewSet(ExportMixin, viewsets.ModelViewSet):
    """CRUD de tareas; filtra por `?proyecto=`, expone `resumen/` y exporta."""

    serializer_class = RegistroSerializer
    export_titulo = "registro_tareas"

    def get_queryset(self):
        qs = Registro.objects.all()
        proyecto = self.request.query_params.get("proyecto")
        return qs.filter(proyecto=proyecto) if proyecto else qs

    @extend_schema(
        summary="Dashboard de tareas: metricas y series para los graficos",
        parameters=[PARAM_PROYECTO],  # usa get_queryset(), asi que respeta el filtro
        responses={200: ResumenTareasSerializer},
    )
    @action(detail=False, methods=["get"])
    def resumen(self, request):
        """Dashboard: métricas (racha, promedios) y series para los 6 gráficos.

        Delega el cálculo en `services.calcular_resumen` (lógica pura, testeable).
        """
        return Response(calcular_resumen(self.get_queryset()))
