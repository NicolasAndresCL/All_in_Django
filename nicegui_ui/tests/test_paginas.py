"""
Smoke tests de las páginas NiceGUI: cada ruta se abre con la API mockeada (responses)
y se verifica que el contenido clave se renderiza — equivalente al test_views_render.py
de la UI Streamlit (mismos fixtures de datos), ahora con nicegui.testing.User.
"""

import responses
from nicegui.testing import User

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
    "id": 1, "fecha": "2026-07-01", "proyecto": "ProyectoA", "tarea": "tareaX",
    "duracion": "02:00:00", "horas": 2.0,
}]
NOTAS = [{"id": 1, "titulo": "NotaUno", "contenido": "# hola", "formato": "md"}]
RESUMEN = {
    "tareas": 1, "proyectos": 1, "horas_total": 2.0, "racha_dias": 1,
    "promedio_diario": 2.0, "promedio_semanal": 2.0,
    "por_proyecto": [{"proyecto": "ProyectoA", "horas": 2.0}],
    "por_tarea": [{"proyecto": "ProyectoA", "tarea": "tareaX", "horas": 2.0}],
    "por_dia": [{"fecha": "2026-07-01", "horas": 2.0}],
    "por_semana": [{"semana": "Sem 27", "horas": 2.0}],
    "por_dia_semana": [{"dia": d, "horas": 0.0} for d in
                       ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes",
                        "Sábado", "Domingo"]],
}
CANALES = {"total": 1, "canales": [
    {"name": "TVN Chile", "url": "https://x.cl", "logo": "https://x.cl/a.png"},
]}


def _mock_api(rsps: responses.RequestsMock) -> None:
    """Registra TODOS los endpoints que consumen las vistas (GETs idempotentes)."""
    rsps.get(f"{BASE}/", json={})  # ping / autenticado
    rsps.get(f"{BASE}/clases/", json=CLASES)
    rsps.get(f"{BASE}/turnos-personales/", json=TURNOS_PERSONALES)
    rsps.get(f"{BASE}/turnos-equipo/", json=TURNOS_EQUIPO)
    rsps.get(f"{BASE}/tareas/resumen/", json=RESUMEN)
    rsps.get(f"{BASE}/tareas/", json=TAREAS)
    rsps.get(f"{BASE}/notas/", json=NOTAS)
    rsps.get(f"{BASE}/tv/canales/", json=CANALES)


# ─── una prueba por página ───────────────────────────────────────────────────
async def test_inicio(user: User) -> None:
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        _mock_api(rsps)
        await user.open("/")
        await user.should_see("Conectado a la API")
        await user.should_see("Resumen")


async def test_calendario(user: User) -> None:
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        _mock_api(rsps)
        await user.open("/calendario")
        await user.should_see("Clases (Santo Tomás)")
        await user.should_see("Guardar semana")


async def test_liveops(user: User) -> None:
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        _mock_api(rsps)
        await user.open("/liveops")
        await user.should_see("Nuevo turno")
        await user.should_see("Importar / Exportar")


async def test_tareas(user: User) -> None:
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        _mock_api(rsps)
        await user.open("/tareas")
        await user.should_see("Tareas Totales")
        await user.should_see("Nueva tarea")


async def test_notas(user: User) -> None:
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        _mock_api(rsps)
        await user.open("/notas")
        await user.should_see("NotaUno")
        await user.should_see("Previsualización")


async def test_tv(user: User) -> None:
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        _mock_api(rsps)
        await user.open("/tv")
        await user.should_see("TVN Chile")


# ─── estados de error (la página avisa, no revienta) ─────────────────────────
async def test_inicio_sin_token_explica_401(user: User) -> None:
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        rsps.get(f"{BASE}/", json={"detail": "no auth"}, status=401)
        await user.open("/")
        await user.should_see("rechaza las credenciales")


async def test_tv_error_api(user: User) -> None:
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        rsps.get(f"{BASE}/tv/canales/", json={"detail": "boom"}, status=503)
        await user.open("/tv")
        await user.should_see("No se pudieron obtener los canales")
