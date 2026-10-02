"""ViewSet del módulo Registro de Tareas (CRUD + resumen + analítica + informe + exportar)."""

from django.http import HttpResponse
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.api import ExportMixin
from core.openapi import MIME_PDF, PARAM_PROYECTO, RESP_PDF, AnaliticaTareasSerializer, ResumenTareasSerializer

from .analitica import calcular_analitica
from .informe import generar_informe_pdf
from .models import Registro
from .serializers import RegistroSerializer
from .services import calcular_resumen, registros_a_frame


@extend_schema_view(list=extend_schema(parameters=[PARAM_PROYECTO]))
class RegistroViewSet(ExportMixin, viewsets.ModelViewSet):
    """CRUD de tareas; filtra por `?proyecto=`, expone `resumen/`, `analitica/`, `informe/`."""

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

        Delega el cálculo en `services.calcular_resumen` (pandas, lógica pura).
        """
        return Response(calcular_resumen(self.get_queryset()))

    @extend_schema(
        summary="Analitica (scikit-learn): tendencia semanal y dias atipicos",
        parameters=[PARAM_PROYECTO],
        responses={200: AnaliticaTareasSerializer},
    )
    @action(detail=False, methods=["get"])
    def analitica(self, request):
        """`LinearRegression` sobre las horas semanales + `IsolationForest` sobre los días."""
        return Response(calcular_analitica(registros_a_frame(self.get_queryset())))

    @extend_schema(
        summary="Informe PDF con graficos seaborn (tendencia, proyectos, mapa de calor)",
        parameters=[PARAM_PROYECTO],
        responses={(200, MIME_PDF): RESP_PDF},
    )
    @action(detail=False, methods=["get"])
    def informe(self, request):
        """PDF con los KPIs del resumen, 3 gráficos seaborn y la tabla de días atípicos."""
        qs = self.get_queryset()
        pdf = generar_informe_pdf(registros_a_frame(qs), calcular_resumen(qs))
        resp = HttpResponse(pdf, content_type=MIME_PDF)
        resp["Content-Disposition"] = 'attachment; filename="informe_tareas.pdf"'
        return resp
