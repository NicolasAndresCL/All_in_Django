"""ViewSet del módulo Notas (CRUD + exportar md/txt)."""

from django.http import HttpResponse
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action

from core.openapi import MIME_MD, MIME_TXT, PARAM_FMT_NOTA, RESP_NOTA_TEXTO

from .models import Nota
from .serializers import NotaSerializer
from .services import markdown_a_texto, slug_archivo


class NotaViewSet(viewsets.ModelViewSet):
    """CRUD de notas; acción `exportar/` para descargar en md o txt."""

    queryset = Nota.objects.all()
    serializer_class = NotaSerializer

    @extend_schema(
        summary="Descarga la nota en markdown o texto plano",
        parameters=[PARAM_FMT_NOTA],
        responses={(200, MIME_MD): RESP_NOTA_TEXTO, (200, MIME_TXT): RESP_NOTA_TEXTO},
    )
    @action(detail=True, methods=["get"])
    def exportar(self, request, pk=None):
        """Descarga la nota: ?fmt=md (markdown crudo) | txt (texto plano)."""
        nota = self.get_object()
        fmt = request.query_params.get("fmt", nota.formato)
        if fmt == "txt":
            contenido, mime, ext = markdown_a_texto(nota.contenido), "text/plain", "txt"
        else:
            contenido, mime, ext = nota.contenido, "text/markdown", "md"
        resp = HttpResponse(contenido, content_type=f"{mime}; charset=utf-8")
        resp["Content-Disposition"] = f'attachment; filename="{slug_archivo(nota.titulo)}.{ext}"'
        return resp
