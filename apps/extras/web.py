"""Vista web básica (templates): panel de inicio con resumen + healthcheck."""

from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render

from apps.calendario.models import Clase, TurnoPersonal
from apps.liveops.models import TurnoEquipo
from apps.notas.models import Nota
from apps.tareas.models import Registro


def healthz(request):
    """Readiness para orquestadores (Compose/K8s): 200 si la BD responde, 503 si no.

    Más barato y explícito que golpear `/api/`. Comprueba la conexión con un SELECT 1.
    """
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
    except Exception as exc:  # noqa: BLE001
        return JsonResponse({"status": "error", "db": str(exc)}, status=503)
    return JsonResponse({"status": "ok"})


def inicio(request):
    """Panel HTML de inicio: métricas agregadas de cada módulo + enlaces a la API."""
    horas_estudio = round(sum(c.horas for c in Clase.objects.all()), 1)
    horas_tareas = round(sum(r.horas for r in Registro.objects.all()), 1)
    ctx = {
        "metricas": [
            ("Horas Santo Tomás", f"{horas_estudio} h"),
            ("Turnos PeYa", TurnoPersonal.objects.filter(es_libre=False).count()),
            ("Turnos equipo", TurnoEquipo.objects.count()),
            ("Horas de Tareas", f"{horas_tareas} h"),
            ("Notas", Nota.objects.count()),
        ],
        "modulos": ["clases", "turnos-personales", "turnos-equipo", "tareas", "notas"],
    }
    return render(request, "index.html", ctx)
