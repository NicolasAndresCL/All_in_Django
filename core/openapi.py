"""
core/openapi.py — Contrato OpenAPI de lo que los serializers NO pueden describir solos.

drf-spectacular deduce el esquema de los serializers, pero las acciones extra
(`exportar`, `imprimir`, `copiar_semana`, `importar`, `resumen`) devuelven PDFs, Excel o
dicts armados a mano: sin anotar, el esquema diria que responden con el serializer del
ViewSet, que es justo lo contrario de lo que hacen. Un esquema que miente es peor que no
tenerlo, porque se cree.

Los serializers de este modulo son **solo de documentacion**: nadie los instancia en
runtime, existen para dar forma a las respuestas en `@extend_schema(responses=...)`.
"""

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse
from rest_framework import serializers

from core.horarios import DIAS_ORDEN, TRABAJADORES

# ─── Parametros de consulta ─────────────────────────────────────────────────
# Los filtros viven en `get_queryset()` a mano (el proyecto no usa django-filter), asi que
# no hay backend del que spectacular pueda deducirlos: se declaran aqui o no existen en el
# esquema.

PARAM_SEMANA = OpenApiParameter(
    name="semana_inicio",
    type=OpenApiTypes.DATE,
    location=OpenApiParameter.QUERY,
    description="Filtra por el lunes de la semana (YYYY-MM-DD).",
)

PARAM_TRABAJADOR = OpenApiParameter(
    name="trabajador",
    type=OpenApiTypes.STR,
    location=OpenApiParameter.QUERY,
    enum=TRABAJADORES,
    description="Filtra por trabajador del equipo.",
)

PARAM_PROYECTO = OpenApiParameter(
    name="proyecto",
    type=OpenApiTypes.STR,
    location=OpenApiParameter.QUERY,
    description="Filtra por nombre exacto de proyecto.",
)

PARAM_FORMATO = OpenApiParameter(
    name="formato",
    type=OpenApiTypes.STR,
    location=OpenApiParameter.QUERY,
    enum=["excel", "pdf"],
    default="excel",
    description="Formato del archivo. Cualquier otro valor cae en 'excel'.",
)

PARAM_BUSCAR = OpenApiParameter(
    name="buscar",
    type=OpenApiTypes.STR,
    location=OpenApiParameter.QUERY,
    description="Filtra canales cuyo nombre contenga el texto (sin distinguir mayusculas).",
)

PARAM_FMT_NOTA = OpenApiParameter(
    name="fmt",
    type=OpenApiTypes.STR,
    location=OpenApiParameter.QUERY,
    enum=["md", "txt"],
    description="Formato de descarga. Por defecto, el `formato` propio de la nota.",
)

# ─── Respuestas de archivo ──────────────────────────────────────────────────
# Todas llevan `Content-Disposition: attachment`, asi que el cliente las descarga.

RESP_PDF = OpenApiResponse(
    OpenApiTypes.BINARY,
    description="PDF con formato (`application/pdf`, `Content-Disposition: attachment`).",
)

RESP_EXPORT = OpenApiResponse(
    OpenApiTypes.BINARY,
    description=(
        "Archivo descargable: `.xlsx` "
        "(`application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`) o `.pdf`, "
        "segun `?formato=`. Exporta el queryset **completo**, sin paginar."
    ),
)

RESP_NOTA_TEXTO = OpenApiResponse(
    OpenApiTypes.STR,
    description="La nota como `text/markdown` o `text/plain` (`charset=utf-8`), como adjunto.",
)

# El media type NO se deduce: sin la clave-tupla (status, media_type) en `responses`,
# spectacular usa los renderers de la vista y declara `application/json` para un PDF.
MIME_PDF = "application/pdf"
MIME_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
MIME_MD = "text/markdown"
MIME_TXT = "text/plain"


# ─── Cuerpos y respuestas JSON ──────────────────────────────────────────────

class CopiarSemanaRequestSerializer(serializers.Serializer):
    """Cuerpo de `copiar_semana`: ambas fechas son el lunes de su semana."""

    origen = serializers.DateField(help_text="Semana de la que se copia.")
    destino = serializers.DateField(help_text="Semana que se REEMPLAZA con la copia.")


class CopiarSemanaRespuestaSerializer(serializers.Serializer):
    copiadas = serializers.IntegerField(help_text="Registros creados en la semana destino.")
    origen = serializers.DateField()
    destino = serializers.DateField()


class ImportarRespuestaSerializer(serializers.Serializer):
    """Resumen de `turnos-equipo/importar/`. `errores` puede venir lleno con 201."""

    importadas = serializers.IntegerField(help_text="Turnos efectivamente guardados (upsert).")
    filas = serializers.IntegerField(help_text="Filas leidas del archivo.")
    agentes = serializers.ListField(child=serializers.CharField())
    semanas = serializers.ListField(child=serializers.DateField())
    errores = serializers.ListField(child=serializers.CharField())


class SerieProyectoSerializer(serializers.Serializer):
    proyecto = serializers.CharField()
    horas = serializers.FloatField()


class SerieTareaSerializer(serializers.Serializer):
    proyecto = serializers.CharField()
    tarea = serializers.CharField()
    horas = serializers.FloatField()


class SerieDiaSerializer(serializers.Serializer):
    fecha = serializers.DateField()
    horas = serializers.FloatField()


class SerieSemanaSerializer(serializers.Serializer):
    semana = serializers.CharField(help_text='Etiqueta de semana, p. ej. "Sem 1".')
    horas = serializers.FloatField()


class SerieDiaSemanaSerializer(serializers.Serializer):
    dia = serializers.ChoiceField(choices=DIAS_ORDEN)
    horas = serializers.FloatField()


class ResumenTareasSerializer(serializers.Serializer):
    """Salida de `tareas/resumen/`: metricas + las 5 series de los graficos."""

    tareas = serializers.IntegerField()
    proyectos = serializers.IntegerField()
    horas_total = serializers.FloatField()
    racha_dias = serializers.IntegerField(help_text="Dias consecutivos con al menos un registro.")
    promedio_diario = serializers.FloatField()
    promedio_semanal = serializers.FloatField()
    por_proyecto = SerieProyectoSerializer(many=True)
    por_tarea = SerieTareaSerializer(many=True)
    por_dia = SerieDiaSerializer(many=True)
    por_semana = SerieSemanaSerializer(many=True)
    por_dia_semana = SerieDiaSemanaSerializer(many=True)


class CanalSerializer(serializers.Serializer):
    name = serializers.CharField()
    url = serializers.URLField()
    logo = serializers.CharField(allow_blank=True)


class CanalesSerializer(serializers.Serializer):
    """Salida de `tv/canales/`. NO pagina: el scraping cabe entero."""

    total = serializers.IntegerField()
    canales = CanalSerializer(many=True)


class ErrorDominioSerializer(serializers.Serializer):
    """Forma de los errores de dominio (`core.exceptions.custom_exception_handler`)."""

    error = serializers.CharField()
    tipo = serializers.CharField(help_text="Nombre de la excepcion, p. ej. 'ArchivoInvalidoError'.")


class DetalleSerializer(serializers.Serializer):
    """Forma estandar de error de DRF (validacion, 401, 404, 429)."""

    detail = serializers.CharField()
