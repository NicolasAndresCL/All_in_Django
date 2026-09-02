"""URLconf raíz: Django Admin + API DRF (router) + esquema OpenAPI + TV + login navegable."""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

from apps.calendario.views import ClaseViewSet, TurnoPersonalViewSet
from apps.extras.web import healthz, inicio
from apps.liveops.views import TurnoEquipoViewSet
from apps.notas.views import NotaViewSet
from apps.tareas.views import RegistroViewSet
from apps.tv.views import CanalesTVView
from core.api import ObtenerToken
from core.metrics import metrics

router = DefaultRouter()
router.register("clases", ClaseViewSet, basename="clase")
router.register("turnos-personales", TurnoPersonalViewSet, basename="turnopersonal")
router.register("turnos-equipo", TurnoEquipoViewSet, basename="turnoequipo")
router.register("tareas", RegistroViewSet, basename="registro")
router.register("notas", NotaViewSet, basename="nota")

urlpatterns = [
    path("", inicio, name="inicio"),
    path("healthz/", healthz, name="healthz"),  # readiness para Compose/K8s
    # Metricas de Prometheus. NO es publico (a diferencia del default de
    # django_prometheus.urls): exige bearer con METRICS_TOKEN, y sin token
    # configurado responde 404. Ver core/metrics.py.
    path("metrics", metrics, name="prometheus-django-metrics"),
    path("admin/", admin.site.urls),
    path("api/token/", ObtenerToken.as_view(), name="api-token"),  # login por token
    path("api/tv/canales/", CanalesTVView.as_view(), name="tv-canales"),
    # Esquema OpenAPI y visor. NO son publicos: heredan IsAuthenticated como el resto
    # de /api/, asi que se consultan con sesion de admin o con token.
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/schema/swagger-ui/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/", include(router.urls)),
    path("api-auth/", include("rest_framework.urls")),  # login para la API navegable
]
