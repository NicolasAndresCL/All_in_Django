"""
apps/tareas/services.py — Cálculo del resumen/dashboard de Registro de Tareas.

Portado de la lógica del dashboard de `all_in_one/views/registro_tareas.py`, como
función pura (recibe los registros, no toca la vista) → fácil de testear.

**Estilo declarativo con pandas/NumPy.** Los registros se convierten UNA vez en un
`DataFrame` (`registros_a_frame`) y cada serie del dashboard es una agregación
encadenada (`groupby(...).sum()`), no un bucle que acumula en `defaultdict`. Ese mismo
DataFrame es la entrada de la analítica (`analitica.py`, scikit-learn) y del informe
PDF (`informe.py`, seaborn): una sola representación tabular para los tres consumidores.

El contrato JSON NO cambió respecto de la versión stdlib: los tests de antes son la
prueba de la refactorización.
"""

from collections.abc import Iterable
from datetime import date

import numpy as np
import pandas as pd

# Nombre de cada día según weekday() (0 = lunes ... 6 = domingo).
DIAS_ES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

COLUMNAS = ["fecha", "proyecto", "tarea", "horas"]
_CAMPOS_ORM = ("fecha", "proyecto", "tarea", "duracion")


def registros_a_frame(registros) -> pd.DataFrame:
    """`Registro`s (QuerySet o iterable de instancias) → DataFrame tipado.

    Columnas: `fecha` (datetime64), `proyecto`, `tarea`, `horas` (float, sin redondear).
    Con un QuerySet se usa `values_list`: trae tuplas y evita instanciar un modelo por
    fila, que con miles de registros es la parte cara del endpoint.
    """
    if hasattr(registros, "values_list"):
        filas = registros.values_list(*_CAMPOS_ORM)
    else:
        filas = ((r.fecha, r.proyecto, r.tarea, r.duracion) for r in registros)
    df = pd.DataFrame(list(filas), columns=[*COLUMNAS[:3], "duracion"])
    return (
        df.assign(
            fecha=pd.to_datetime(df["fecha"]),
            horas=pd.to_timedelta(df["duracion"]).dt.total_seconds() / 3600,
        )
        .drop(columns="duracion")
        .astype({"proyecto": "string", "tarea": "string", "horas": "float64"})
    )


def calcular_racha(fechas: Iterable, hoy: date | None = None) -> int:
    """
    Días consecutivos con actividad contando hacia atrás desde hoy (o ayer).

    Si el registro más reciente no es de hoy ni de ayer, la racha es 0. Vectorizado con
    NumPy: con las fechas únicas en orden descendente, la racha es el largo del primer
    tramo cuyos saltos (`np.diff`) valen exactamente 1 día.
    """
    hoy = np.datetime64(hoy or date.today(), "D")
    dias = np.unique(np.array(list(fechas), dtype="datetime64[D]"))[::-1]
    if dias.size == 0 or (hoy - dias[0]).astype(int) not in (0, 1):
        return 0
    rotos = np.flatnonzero(-np.diff(dias).astype(int) != 1)
    return int(rotos[0] + 1) if rotos.size else int(dias.size)


def _serie(agregado: pd.Series, nombre: str) -> list[dict]:
    """Serie agregada → `[{<claves del índice>, horas}]`, redondeada a 2 decimales.

    `to_dict("records")` devuelve tipos nativos de Python (int/float/str), así que el
    resultado se serializa a JSON sin conversores para `numpy.int64`.
    """
    return agregado.round(2).rename(nombre).reset_index().to_dict("records")


def calcular_resumen(registros, hoy: date | None = None) -> dict:
    """
    Métricas + series del dashboard a partir de los `Registro`.

    Claves devueltas:
      tareas, proyectos, horas_total, racha_dias, promedio_diario, promedio_semanal,
      por_proyecto  -> [{proyecto, horas}]           (esfuerzo por proyecto)
      por_tarea     -> [{proyecto, tarea, horas}]    (jerarquía / sunburst)
      por_dia       -> [{fecha, horas}]              (intensidad diaria / acumulado)
      por_semana    -> [{semana, horas}]             (productividad semanal)
      por_dia_semana-> [{dia, horas}]                (Lunes..Domingo)
    """
    df = registros_a_frame(registros)
    iso = df["fecha"].dt.isocalendar()
    df = df.assign(anio_iso=iso["year"], semana_iso=iso["week"], dow=df["fecha"].dt.weekday)

    horas_total = float(df["horas"].sum())
    dias_unicos = df["fecha"].nunique()
    por_semana = df.groupby(["anio_iso", "semana_iso"])["horas"].sum()
    por_dia = df.groupby("fecha")["horas"].sum()
    # reindex(range(7)): los 7 días SIEMPRE, con 0 donde no hubo actividad.
    por_dow = df.groupby("dow")["horas"].sum().reindex(range(7), fill_value=0.0)

    return {
        "tareas": len(df),
        "proyectos": int(df["proyecto"].nunique()),
        "horas_total": round(horas_total, 2),
        "racha_dias": calcular_racha(df["fecha"].dt.date, hoy),
        "promedio_diario": round(horas_total / dias_unicos, 2) if dias_unicos else 0,
        "promedio_semanal": round(horas_total / len(por_semana), 2) if len(por_semana) else 0,
        "por_proyecto": _serie(df.groupby("proyecto")["horas"].sum(), "horas"),
        "por_tarea": _serie(df.groupby(["proyecto", "tarea"])["horas"].sum(), "horas"),
        "por_dia": _serie(por_dia.set_axis(por_dia.index.strftime("%Y-%m-%d")).rename_axis("fecha"), "horas"),
        "por_semana": [
            {"semana": f"Sem {semana}", "horas": float(horas)}
            for (_anio, semana), horas in por_semana.round(2).items()
        ],
        "por_dia_semana": _serie(por_dow.set_axis(DIAS_ES).rename_axis("dia"), "horas"),
    }
