"""
apps/tareas/services.py — Cálculo del resumen/dashboard de Registro de Tareas.

Portado de la lógica del dashboard de `all_in_one/views/registro_tareas.py`, pero
como función pura (recibe los registros, no toca la vista) → fácil de testear.
Devuelve las métricas (incluida la **racha** de días consecutivos) y las series que
la UI dibuja con Plotly. Sin dependencias externas: solo stdlib.
"""

from collections import defaultdict
from datetime import date, timedelta

# Nombre de cada día según weekday() (0 = lunes ... 6 = domingo).
DIAS_ES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def _horas(registro) -> float:
    """Horas (float, sin redondear) de un Registro a partir de su duración."""
    return registro.duracion.total_seconds() / 3600


def calcular_racha(fechas: set, hoy: date | None = None) -> int:
    """
    Días consecutivos con actividad contando hacia atrás desde hoy (o ayer).

    Si el registro más reciente no es de hoy ni de ayer, la racha es 0. Réplica
    de la lógica del dashboard de all_in_one.
    """
    hoy = hoy or date.today()
    racha = 0
    check = hoy
    for f in sorted(fechas, reverse=True):
        if f == check or f == check - timedelta(days=1):
            racha += 1
            check = f
        else:
            break
    return racha


def calcular_resumen(registros, hoy: date | None = None) -> dict:
    """
    Métricas + series del dashboard a partir de una lista de `Registro`.

    Claves devueltas:
      tareas, proyectos, horas_total, racha_dias, promedio_diario, promedio_semanal,
      por_proyecto  -> [{proyecto, horas}]           (esfuerzo por proyecto)
      por_tarea     -> [{proyecto, tarea, horas}]    (jerarquía / sunburst)
      por_dia       -> [{fecha, horas}]              (intensidad diaria / acumulado)
      por_semana    -> [{semana, horas}]             (productividad semanal)
      por_dia_semana-> [{dia, horas}]                (Lunes..Domingo)
    """
    registros = list(registros)
    horas_total = sum(_horas(r) for r in registros)

    proy = defaultdict(float)
    tarea = defaultdict(float)
    dia = defaultdict(float)
    semana = defaultdict(float)
    dow = [0.0] * 7
    fechas = set()

    for r in registros:
        h = _horas(r)
        proy[r.proyecto] += h
        tarea[(r.proyecto, r.tarea)] += h
        dia[r.fecha] += h
        iso = r.fecha.isocalendar()  # (año_iso, semana_iso, día_iso)
        semana[(iso[0], iso[1])] += h
        dow[r.fecha.weekday()] += h
        fechas.add(r.fecha)

    dias_unicos = len(fechas)
    semanas_unicas = len(semana)

    return {
        "tareas": len(registros),
        "proyectos": len(proy),
        "horas_total": round(horas_total, 2),
        "racha_dias": calcular_racha(fechas, hoy),
        "promedio_diario": round(horas_total / dias_unicos, 2) if dias_unicos else 0,
        "promedio_semanal": round(horas_total / semanas_unicas, 2) if semanas_unicas else 0,
        "por_proyecto": [
            {"proyecto": p, "horas": round(h, 2)} for p, h in sorted(proy.items())
        ],
        "por_tarea": [
            {"proyecto": p, "tarea": t, "horas": round(h, 2)}
            for (p, t), h in sorted(tarea.items())
        ],
        "por_dia": [
            {"fecha": f.isoformat(), "horas": round(h, 2)} for f, h in sorted(dia.items())
        ],
        "por_semana": [
            {"semana": f"Sem {w}", "horas": round(h, 2)}
            for (_y, w), h in sorted(semana.items())
        ],
        "por_dia_semana": [
            {"dia": DIAS_ES[i], "horas": round(dow[i], 2)} for i in range(7)
        ],
    }
