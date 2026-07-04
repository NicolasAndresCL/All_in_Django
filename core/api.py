"""
core/api.py — Utilidades compartidas para la capa REST.

`ExportMixin` añade una acción `GET .../exportar/?formato=excel|pdf` a cualquier
ViewSet, reutilizando `core.export`. Evita repetir la lógica de exportación.
"""

from django.http import HttpResponse
from rest_framework.decorators import action

from core.export import generar_excel, generar_pdf

_TIPOS = {
    "excel": ("xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    "pdf": ("pdf", "application/pdf"),
}


class ExportMixin:
    """Requiere un ViewSet DRF (usa get_queryset / get_serializer / filter_queryset)."""

    export_titulo = "datos"

    @action(detail=False, methods=["get"])
    def exportar(self, request):
        formato = request.query_params.get("formato", "excel").lower()
        datos = self.get_serializer(self.filter_queryset(self.get_queryset()), many=True).data
        columnas = list(datos[0].keys()) if datos else []
        filas = [dict(d) for d in datos]  # OrderedDict → dict

        ext, mime = _TIPOS.get(formato, _TIPOS["excel"])
        if formato == "pdf":
            contenido = generar_pdf(self.export_titulo, columnas, filas)
        else:
            contenido = generar_excel(columnas, filas, self.export_titulo)

        resp = HttpResponse(contenido, content_type=mime)
        resp["Content-Disposition"] = f'attachment; filename="{self.export_titulo}.{ext}"'
        return resp
