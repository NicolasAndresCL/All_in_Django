"""ViewSet del módulo Registro de Tareas (CRUD + resumen + exportar)."""

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import viewsets

from core.api import ExportMixin

from .models import Registro
from .serializers import RegistroSerializer
from .services import calcular_resumen


class RegistroViewSet(ExportMixin, viewsets.ModelViewSet):
    """CRUD de tareas; filtra por `?proyecto=`, expone `resumen/` y exporta."""

    serializer_class = RegistroSerializer
    export_titulo = "registro_tareas"

    def get_queryset(self):
        qs = Registro.objects.all()
        proyecto = self.request.query_params.get("proyecto")
        return qs.filter(proyecto=proyecto) if proyecto else qs

    @action(detail=False, methods=["get"])
    def resumen(self, request):
        """Dashboard: métricas (racha, promedios) y series para los 6 gráficos.

        Delega el cálculo en `services.calcular_resumen` (lógica pura, testeable).
        """
        return Response(calcular_resumen(self.get_queryset()))
