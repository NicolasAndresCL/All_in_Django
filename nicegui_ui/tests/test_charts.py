"""Tests de las figuras del dashboard de Tareas (charts.py, sin runtime de UI)."""

from nicegui_ui.charts import construir_figuras

# Resumen con la forma que devuelve /api/tareas/resumen/.
RESUMEN = {
    "tareas": 3, "proyectos": 2, "horas_total": 6.0, "racha_dias": 2,
    "promedio_diario": 3.0, "promedio_semanal": 6.0,
    "por_proyecto": [{"proyecto": "A", "horas": 3.0}, {"proyecto": "B", "horas": 3.0}],
    "por_tarea": [
        {"proyecto": "A", "tarea": "x", "horas": 2.0},
        {"proyecto": "A", "tarea": "y", "horas": 1.0},
        {"proyecto": "B", "tarea": "z", "horas": 3.0},
    ],
    "por_dia": [{"fecha": "2026-07-01", "horas": 4.0}, {"fecha": "2026-07-02", "horas": 2.0}],
    "por_semana": [{"semana": "Sem 27", "horas": 6.0}],
    "por_dia_semana": [{"dia": d, "horas": 0.0} for d in
                       ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]],
}

CLAVES = {"jerarquia", "esfuerzo", "intensidad", "semanal", "dia_semana", "acumulado"}


def test_construye_las_seis_figuras():
    figs = construir_figuras(RESUMEN)
    assert set(figs) == CLAVES
    assert all(figs[k] is not None for k in CLAVES)
    assert figs["jerarquia"].data  # el sunburst tiene trazas


def test_sin_dias_las_figuras_temporales_son_none():
    vacio = {**RESUMEN, "por_dia": [], "por_tarea": []}
    figs = construir_figuras(vacio)
    assert figs["intensidad"] is None
    assert figs["acumulado"] is None
    assert figs["jerarquia"] is None
    # Las que solo dependen de agregados siguen construyéndose.
    assert figs["esfuerzo"] is not None
    assert figs["dia_semana"] is not None
    assert figs["semanal"] is not None
