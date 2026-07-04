"""URLconf raíz: Django Admin + API DRF (router) + endpoint TV + login navegable."""

from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.calendario.views import ClaseViewSet, TurnoPersonalViewSet
from apps.liveops.views import TurnoEquipoViewSet
from apps.notas.views import NotaViewSet
from apps.tareas.views import RegistroViewSet
from apps.extras.web import inicio
from apps.tv.views import CanalesTVView

router = DefaultRouter()
router.register("clases", ClaseViewSet, basename="clase")
router.register("turnos-personales", TurnoPersonalViewSet, basename="turnopersonal")
router.register("turnos-equipo", TurnoEquipoViewSet, basename="turnoequipo")
router.register("tareas", RegistroViewSet, basename="registro")
router.register("notas", NotaViewSet, basename="nota")

urlpatterns = [
    path("", inicio, name="inicio"),
    path("admin/", admin.site.urls),
    path("api/tv/canales/", CanalesTVView.as_view(), name="tv-canales"),
    path("api/", include(router.urls)),
    path("api-auth/", include("rest_framework.urls")),  # login para la API navegable
]
