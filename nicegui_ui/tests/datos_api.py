"""
Datos de ejemplo con la forma que devuelve la API DRF, y el mock de sus GET.

Vive aparte porque lo comparten los tests de humo (`test_paginas.py`) y los de
interaccion (`test_interaccion.py`): si cada archivo tuviera su copia, arreglar la forma
de una respuesta en uno dejaria al otro probando contra un contrato que ya no existe.
"""

import responses

BASE = "http://testserver/api"

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
    # 40 semanas, como la base real: con una sola, ningún test podía ver que las
    # etiquetas del eje de "Productividad semanal" se montaban a 360 px.
    "por_semana": [{"semana": f"Sem {n}", "horas": 2.0} for n in range(3, 43)],
    "por_dia_semana": [{"dia": d, "horas": 0.0} for d in
                       ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes",
                        "Sábado", "Domingo"]],
}
ANALITICA = {
    "tendencia": {
        "semanas": 4, "pendiente": 2.0, "r2": 1.0, "proyeccion": 18.0, "direccion": "sube",
        "ajuste": [{"semana": f"2026-06-{d:02d}", "horas": h, "ajustada": h}
                   for d, h in [(8, 10.0), (15, 12.0), (22, 14.0), (29, 16.0)]],
    },
    "atipicos": [{"fecha": "2026-06-30", "horas": 20.0, "registros": 9, "puntaje": -0.12,
                  "motivo": "más registros de lo habitual"}],
    "requisitos": {"min_semanas": 4, "min_dias": 10},
}
CANALES = {"total": 1, "canales": [
    {"name": "TVN Chile", "url": "https://x.cl", "logo": "https://x.cl/a.png"},
]}


def mock_api(rsps: responses.RequestsMock, *, tareas: list[dict] | None = None) -> None:
    """Registra TODOS los endpoints que consumen las vistas (GETs idempotentes)."""
    rsps.get(f"{BASE}/", json={})  # ping / autenticado
    rsps.get(f"{BASE}/clases/", json=CLASES)
    rsps.get(f"{BASE}/turnos-personales/", json=TURNOS_PERSONALES)
    rsps.get(f"{BASE}/turnos-equipo/", json=TURNOS_EQUIPO)
    rsps.get(f"{BASE}/tareas/resumen/", json=RESUMEN)
    rsps.get(f"{BASE}/tareas/analitica/", json=ANALITICA)
    rsps.get(f"{BASE}/tareas/", json=TAREAS if tareas is None else tareas)
    rsps.get(f"{BASE}/notas/", json=NOTAS)
    rsps.get(f"{BASE}/tv/canales/", json=CANALES)
