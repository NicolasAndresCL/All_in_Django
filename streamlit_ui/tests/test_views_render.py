"""
Smoke tests de las vistas Streamlit: ejecutan cada `render()` completo contra una
API mockeada (responses) y verifican que la página se dibuja sin excepciones.

Cubre el hueco que dejaban los tests previos: `test_app.py` solo probaba que la
navegación se construyera, y `test_tareas_dashboard`/`test_gantt` solo probaban
funciones puras. Aquí se ejercita el árbol de widgets real de cada vista con datos
representativos (incluye tablas, métricas y gráficos Gantt/Plotly).
"""

import os

# La URL base se fija ANTES de importar las vistas: `get_client()` la cachea
# (@st.cache_resource) a partir de esta variable, y responses intercepta ese host.
os.environ["API_BASE"] = "http://testserver/api"

import responses
from streamlit.testing.v1 import AppTest

BASE = "http://testserver/api"

# ─── datos de ejemplo (forma que devuelve la API DRF) ────────────────────────
CLASES = [{
    "id": 1, "semana_inicio": "2026-06-29", "dia": "Lunes", "asignatura": "Mate",
    "entrada": "08:00:00", "salida": "10:00:00", "horas": 2.0,
}]
TURNOS_PERSONALES = [{
    "id": 1, "semana_inicio": "2026-06-29", "dia": "Lunes", "es_libre": False,
    "entrada": "18:00:00", "salida": "23:00:00", "neto": 5.0, "extra": 0.0,
}]
TURNOS_EQUIPO = [{
    "id": 1, "semana_inicio": "2026-06-29", "trabajador": "Nico", "dia": "Lunes",
    "es_libre": False, "entrada": "09:00:00", "salida": "18:00:00", "neto": 8.0, "extra": 0.0,
}]
TAREAS = [{
    "id": 1, "fecha": "2026-07-01", "proyecto": "A", "tarea": "x",
    "duracion": "02:00:00", "horas": 2.0,
}]
NOTAS = [{"id": 1, "titulo": "Nota", "contenido": "# hola", "formato": "md"}]
RESUMEN = {
    "tareas": 1, "proyectos": 1, "horas_total": 2.0, "racha_dias": 1,
    "promedio_diario": 2.0, "promedio_semanal": 2.0,
    "por_proyecto": [{"proyecto": "A", "horas": 2.0}],
    "por_tarea": [{"proyecto": "A", "tarea": "x", "horas": 2.0}],
    "por_dia": [{"fecha": "2026-07-01", "horas": 2.0}],
    "por_semana": [{"semana": "Sem 27", "horas": 2.0}],
    "por_dia_semana": [{"dia": d, "horas": 0.0} for d in
                       ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]],
}
CANALES = {"total": 1, "canales": [
    {"name": "TVN Chile", "url": "https://x.cl", "logo": "https://x.cl/a.png"},
]}


def _app(modulo: str) -> AppTest:
    """AppTest que importa la vista `modulo` y ejecuta su `render` (como en app.py).

    Se usa `from_string` en vez de `from_function` porque esta última ejecuta solo
    el cuerpo de la función en un namespace aislado (sin el `import streamlit as st`
    del módulo). El script se ejecuta con el sys.path del proceso, donde el conftest
    del paquete ya insertó `streamlit_ui/`, así que `from views import ...` resuelve.
    """
    script = f"from views import {modulo}\n{modulo}.render()\n"
    return AppTest.from_string(script, default_timeout=30)


def _correr(modulo: str) -> AppTest:
    """Ejecuta la vista y verifica que no lanzó excepciones."""
    at = _app(modulo).run()
    assert not at.exception, [e.value for e in at.exception]
    return at


# ─── una prueba por vista ────────────────────────────────────────────────────
@responses.activate
def test_inicio_render():
    responses.get(f"{BASE}/", json={})  # ping()
    responses.get(f"{BASE}/clases/", json=CLASES)
    responses.get(f"{BASE}/turnos-personales/", json=TURNOS_PERSONALES)
    responses.get(f"{BASE}/turnos-equipo/", json=TURNOS_EQUIPO)
    responses.get(f"{BASE}/tareas/", json=TAREAS)
    responses.get(f"{BASE}/notas/", json=NOTAS)
    at = _correr("inicio")
    assert at.title[0].value.startswith("🏠")


@responses.activate
def test_calendario_render():
    responses.get(f"{BASE}/clases/", json=CLASES)
    responses.get(f"{BASE}/turnos-personales/", json=TURNOS_PERSONALES)
    at = _correr("calendario")
    # Las tres pestañas se construyen (Clases, Turnos, Impresión y Gantt).
    assert len(at.tabs) == 3


@responses.activate
def test_liveops_render():
    responses.get(f"{BASE}/turnos-equipo/", json=TURNOS_EQUIPO)
    at = _correr("liveops")
    assert at.title[0].value.startswith("👥")


@responses.activate
def test_tareas_render():
    responses.get(f"{BASE}/tareas/", json=TAREAS)
    responses.get(f"{BASE}/tareas/resumen/", json=RESUMEN)
    at = _correr("tareas")
    assert at.title[0].value.startswith("✅")


@responses.activate
def test_notas_render():
    responses.get(f"{BASE}/notas/", json=NOTAS)
    at = _correr("notas")
    assert at.title[0].value.startswith("📝")


@responses.activate
def test_tv_render():
    responses.get(f"{BASE}/tv/canales/", json=CANALES)
    at = _correr("tv")
    assert at.title[0].value.startswith("📺")


# ─── vistas ante fallos de la API (no deben romperse) ────────────────────────
@responses.activate
def test_inicio_sin_backend_muestra_error():
    # ping() falla (500) → la vista muestra st.error y hace st.stop() sin excepción.
    responses.get(f"{BASE}/", status=500)
    at = _app("inicio").run()
    assert not at.exception
    assert at.error  # se pintó al menos un mensaje de error


@responses.activate
def test_tv_error_api():
    responses.get(f"{BASE}/tv/canales/", status=503)
    at = _app("tv").run()
    assert not at.exception
    assert at.error
