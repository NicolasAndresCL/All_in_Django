"""ViewSet del módulo LiveOps (CRUD + importar CSV/Excel + exportar + imprimir)."""

from django.http import HttpResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.api import ExportMixin
from core.exceptions import ArchivoInvalidoError
from core.horarios import DIAS_ORDEN
from core.horarios_export import generar_pdf_equipo
from core.logging import get_logger

from .models import TurnoEquipo
from .serializers import ImportarTurnosSerializer, TurnoEquipoSerializer
from .services import guardar_turnos, leer_tabla, preparar_turnos_equipo

logger = get_logger(__name__)


class TurnoEquipoViewSet(ExportMixin, viewsets.ModelViewSet):
    """CRUD de turnos del equipo; filtra por semana/trabajador, importa y exporta."""

    serializer_class = TurnoEquipoSerializer
    export_titulo = "turnos_equipo"

    def get_queryset(self):
        qs = TurnoEquipo.objects.all()
        semana = self.request.query_params.get("semana_inicio")
        trabajador = self.request.query_params.get("trabajador")
        if semana:
            qs = qs.filter(semana_inicio=semana)
        if trabajador:
            qs = qs.filter(trabajador=trabajador)
        return qs

    @action(detail=False, methods=["post"], serializer_class=ImportarTurnosSerializer)
    def importar(self, request):
        """Importa turnos desde un CSV/Excel (campo multipart 'archivo')."""
        archivo = request.FILES.get("archivo")
        if archivo is None:
            raise ArchivoInvalidoError("Falta el archivo (campo 'archivo').")

        df = leer_tabla(archivo, archivo.name)
        filas, resumen, errores = preparar_turnos_equipo(df)
        guardadas = guardar_turnos(
            filas,
            on_ok=lambda n: logger.info("Importadas %s filas de turnos", n),
            on_error=lambda msg: errores.append(msg),
        )
        return Response(
            {"importadas": guardadas, **resumen, "errores": errores},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["get"])
    def imprimir(self, request):
        """PDF con formato de los turnos de `?semana_inicio=` (opcional `?trabajador=`)."""
        semana = request.query_params.get("semana_inicio")
        trabajador = request.query_params.get("trabajador")
        qs = self.filter_queryset(self.get_queryset())
        campos = ["dia", "entrada", "salida", "bruto", "neto", "extra", "es_libre"]
        if not trabajador:
            campos = ["trabajador", *campos]
        filas = sorted(
            qs.values(*campos),
            key=lambda r: (r.get("trabajador", ""),
                           DIAS_ORDEN.index(r["dia"]) if r["dia"] in DIAS_ORDEN else 99),
        )
        etiqueta = trabajador or "General"
        titulo = f"Horarios {etiqueta} - {semana or 'todas las semanas'}"
        resp = HttpResponse(generar_pdf_equipo(filas, titulo), content_type="application/pdf")
        resp["Content-Disposition"] = f'attachment; filename="Horario_{semana or "equipo"}.pdf"'
        return resp
