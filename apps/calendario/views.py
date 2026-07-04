"""ViewSets del módulo Calendario (CRUD + exportar + imprimir + copiar semana)."""

from django.http import HttpResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.api import ExportMixin
from core.horarios import DIAS_ORDEN
from core.horarios_export import (
    generar_pdf_estudio,
    generar_pdf_laboral,
    generar_pdf_maestro,
)

from .models import Clase, TurnoPersonal
from .serializers import ClaseSerializer, TurnoPersonalSerializer
from .services import copiar_clases, copiar_turnos_personales


def _pdf(contenido: bytes, nombre: str) -> HttpResponse:
    resp = HttpResponse(contenido, content_type="application/pdf")
    resp["Content-Disposition"] = f'attachment; filename="{nombre}"'
    return resp


def _por_dia(filas: list[dict]) -> list[dict]:
    """Ordena las filas de Lunes a Domingo (los días son CharField con choices)."""
    return sorted(filas, key=lambda r: DIAS_ORDEN.index(r["dia"]) if r.get("dia") in DIAS_ORDEN else 99)


def _copiar_semana(request, copiar_fn):
    """Cuerpo común de la acción copiar_semana: valida origen/destino y delega."""
    origen = request.data.get("origen")
    destino = request.data.get("destino")
    if not origen or not destino:
        return Response({"detail": "Faltan 'origen' y/o 'destino'."},
                        status=status.HTTP_400_BAD_REQUEST)
    n = copiar_fn(origen, destino)
    return Response({"copiadas": n, "origen": origen, "destino": destino},
                    status=status.HTTP_201_CREATED)


class ClaseViewSet(ExportMixin, viewsets.ModelViewSet):
    """CRUD de clases; filtra por `?semana_inicio=`, exporta, imprime y copia semanas."""

    serializer_class = ClaseSerializer
    export_titulo = "clases"

    def get_queryset(self):
        qs = Clase.objects.all()
        semana = self.request.query_params.get("semana_inicio")
        return qs.filter(semana_inicio=semana) if semana else qs

    @action(detail=False, methods=["get"])
    def imprimir(self, request):
        """PDF con formato del horario de estudio de `?semana_inicio=`."""
        semana = request.query_params.get("semana_inicio")
        filas = _por_dia(list(
            Clase.objects.filter(semana_inicio=semana)
            .values("dia", "asignatura", "entrada", "salida", "horas")
        )) if semana else []
        return _pdf(generar_pdf_estudio(filas, semana or "-"), f"Estudio_{semana}.pdf")

    @action(detail=False, methods=["get"])
    def imprimir_maestro(self, request):
        """PDF unificado (estudio + trabajo) de `?semana_inicio=`."""
        semana = request.query_params.get("semana_inicio")
        clases = list(Clase.objects.filter(semana_inicio=semana)
                      .values("dia", "asignatura", "entrada", "salida", "horas")) if semana else []
        turnos = list(TurnoPersonal.objects.filter(semana_inicio=semana)
                      .values("dia", "entrada", "salida", "neto", "es_libre")) if semana else []
        return _pdf(generar_pdf_maestro(clases, turnos, semana or "-"), f"Master_{semana}.pdf")

    @action(detail=False, methods=["post"])
    def copiar_semana(self, request):
        """Copia las clases de `origen` a `destino` (reemplaza destino)."""
        return _copiar_semana(request, copiar_clases)


class TurnoPersonalViewSet(ExportMixin, viewsets.ModelViewSet):
    """CRUD de turnos personales; filtra por `?semana_inicio=`, exporta, imprime y copia."""

    serializer_class = TurnoPersonalSerializer
    export_titulo = "turnos_personales"

    def get_queryset(self):
        qs = TurnoPersonal.objects.all()
        semana = self.request.query_params.get("semana_inicio")
        return qs.filter(semana_inicio=semana) if semana else qs

    @action(detail=False, methods=["get"])
    def imprimir(self, request):
        """PDF con formato del horario laboral de `?semana_inicio=`."""
        semana = request.query_params.get("semana_inicio")
        filas = _por_dia(list(
            TurnoPersonal.objects.filter(semana_inicio=semana)
            .values("dia", "entrada", "salida", "bruto", "neto", "extra", "es_libre")
        )) if semana else []
        return _pdf(generar_pdf_laboral(filas, semana or "-"), f"PeYa_{semana}.pdf")

    @action(detail=False, methods=["post"])
    def copiar_semana(self, request):
        """Copia los turnos personales de `origen` a `destino` (reemplaza destino)."""
        return _copiar_semana(request, copiar_turnos_personales)
