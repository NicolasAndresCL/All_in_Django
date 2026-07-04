"""ViewSet del módulo Notas (CRUD + exportar md/txt)."""

from django.http import HttpResponse
from rest_framework import viewsets
from rest_framework.decorators import action

from .models import Nota
from .serializers import NotaSerializer
from .services import markdown_a_texto, slug_archivo


class NotaViewSet(viewsets.ModelViewSet):
    """CRUD de notas; acción `exportar/` para descargar en md o txt."""

    queryset = Nota.objects.all()
    serializer_class = NotaSerializer

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
