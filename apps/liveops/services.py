"""
apps/liveops/services.py — Importación de turnos de equipo desde CSV/Excel.

Portado de all_in_one/core/liveops_import.py y adaptado al ORM de Django.
Mapea agentes a Babi/Jorge/Manu/Nico, deriva semana/día desde la fecha y deja que
el modelo calcule bruto/neto/extra al guardar. `guardar_turnos` admite callbacks
(`on_ok` / `on_error`) para desacoplar la lógica de la vista.
"""

import re
import unicodedata
from collections.abc import Callable
from datetime import time

import numpy as np
import pandas as pd

from core.exceptions import ArchivoInvalidoError, ImportacionError
from core.horarios import DIAS_ORDEN, TRABAJADORES
from core.logging import get_logger

from .models import TurnoEquipo

logger = get_logger(__name__)


def _norm(s) -> str:
    txt = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return txt.lower().strip()


MAPA_TRABAJADORES = {
    "barbara vilches": "Babi", "barbara": "Babi", "babi": "Babi", "bv": "Babi",
    "jorge escalona": "Jorge", "jorge": "Jorge", "je": "Jorge",
    "manuel meza": "Manu", "manuel": "Manu", "manu": "Manu", "mm": "Manu",
    "nicolas cano": "Nico", "nicolas": "Nico", "nico": "Nico", "nc": "Nico",
}


def normalizar_trabajador(valor) -> str:
    k = _norm(valor)
    if k in MAPA_TRABAJADORES:
        return MAPA_TRABAJADORES[k]
    for corto in TRABAJADORES:
        if _norm(corto) == k:
            return corto
    return str(valor).strip()


def parse_hora(v):
    """Devuelve datetime.time o None (None = libre / sin turno)."""
    if isinstance(v, time):
        return v
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    s = str(v).strip()
    if s.lower() in ("", "—", "-", "libre", "nan", "nat", "none"):
        return None
    m = re.match(r"^(\d{1,2}):(\d{2})", s)
    return time(int(m.group(1)), int(m.group(2))) if m else None


def leer_tabla(file, nombre: str) -> pd.DataFrame:
    """Lee un archivo (CSV o Excel) a DataFrame; error claro si no se puede."""
    try:
        if str(nombre).lower().endswith(".csv"):
            return pd.read_csv(file, encoding="utf-8-sig")
        return pd.read_excel(file)
    except Exception as exc:  # noqa: BLE001
        raise ArchivoInvalidoError(f"No se pudo leer el archivo: {exc}") from exc


def preparar_turnos_equipo(df: pd.DataFrame):
    """
    Transforma el DataFrame en filas de TurnoEquipo.

    Devuelve (filas, resumen, errores). Cada fila es un dict que `guardar_turnos`
    hace upsert: semana_inicio(date), trabajador, dia, entrada(time|None),
    salida(time|None), es_libre(bool).
    """
    cols = {_norm(c): c for c in df.columns}

    def col(*nombres):
        for n in nombres:
            if _norm(n) in cols:
                return cols[_norm(n)]
        return None

    c_fecha = col("Fecha", "Date")
    c_trab = col("Agente", "Trabajador", "Agent")
    c_acr = col("Acrónimo", "Acronimo", "Acro")
    c_ent = col("Entrada", "In")
    c_sal = col("Salida", "Out")
    c_est = col("Estado", "Status")

    if c_fecha is None:
        raise ArchivoInvalidoError("El archivo no tiene columna 'Fecha'.")
    if c_trab is None and c_acr is None:
        raise ArchivoInvalidoError("El archivo no tiene columna 'Agente'/'Trabajador'.")

    # Vectorizado con máscaras booleanas en vez de `iterrows()`: cada regla de validación
    # es UNA expresión sobre la columna entera. Las reglas son excluyentes y en orden
    # (sin agente → sin fecha → fecha inválida), como en la versión fila a fila.
    agente = df[c_trab] if c_trab else df[c_acr]
    # format="mixed": parsea CADA celda por separado. Sin él pandas infiere el formato de
    # la primera y anula (NaT) las que lo usen distinto — un Excel a mano los mezcla.
    fecha = pd.to_datetime(df[c_fecha], format="mixed", errors="coerce")
    sin_agente = agente.isna()
    sin_fecha = ~sin_agente & df[c_fecha].isna()
    invalida = ~sin_agente & ~sin_fecha & fecha.isna()
    # np.select = tabla condición → mensaje, evaluada en orden POSICIONAL (el de las
    # filas del archivo, aunque el índice venga desordenado). Fila = posición + 2 en el
    # caso habitual (índice 0..n-1): +1 base-1, +1 encabezado.
    # dtype=object explícito: con 0 filas, `map(repr)` sobre una columna float conserva
    # float64 y concatenar texto revienta (TypeError) — un archivo vacío es entrada válida.
    nfila = pd.Series([f"Fila {i + 2}" for i in df.index], index=df.index, dtype=object)
    fecha_repr = pd.Series([repr(v) for v in df[c_fecha]], index=df.index, dtype=object)
    mensajes = np.select(
        [sin_agente, sin_fecha, invalida],
        [nfila + ": sin agente.",
         nfila + ": sin fecha.",
         nfila + ": fecha inválida (" + fecha_repr + ")."],
        default="",
    )
    errores = [m for m in mensajes if m]

    ok = ~(sin_agente | sin_fecha | invalida)
    dia_semana = fecha[ok].dt.weekday
    entrada = df.loc[ok, c_ent].map(parse_hora) if c_ent else pd.Series(None, index=df.index[ok], dtype=object)
    salida = df.loc[ok, c_sal].map(parse_hora) if c_sal else pd.Series(None, index=df.index[ok], dtype=object)
    estado = df.loc[ok, c_est].map(_norm) if c_est else pd.Series("", index=df.index[ok])
    es_libre = (estado == "libre") | entrada.isna() | salida.isna()

    turnos = pd.DataFrame({
        "semana_inicio": (fecha[ok] - pd.to_timedelta(dia_semana, unit="D")).dt.date,
        "trabajador": agente[ok].map(normalizar_trabajador),
        "dia": dia_semana.map(dict(enumerate(DIAS_ORDEN))),
        # astype(object) + where: un día libre lleva None, no NaT/NaN.
        "entrada": entrada.astype(object).where(~es_libre, None),
        "salida": salida.astype(object).where(~es_libre, None),
        "es_libre": es_libre,
    })
    filas = turnos.to_dict("records")

    resumen = {
        "filas": len(filas),
        "agentes": sorted({f["trabajador"] for f in filas}),
        "semanas": sorted({f["semana_inicio"].isoformat() for f in filas}),
    }
    return filas, resumen, errores


def guardar_turnos(filas, on_ok: Callable[[int], None] = None,
                   on_error: Callable[[str], None] = None) -> int:
    """Crea/actualiza TurnoEquipo por (semana, trabajador, dia). Usa callbacks opcionales."""
    guardadas = 0
    for fila in filas:
        try:
            # No se usa update_or_create: pasa `update_fields` a save() y entonces los
            # campos calculados (bruto/neto/extra) no se recalcularían al actualizar.
            # Un save() completo deja que el modelo recalcule todo.
            turno = TurnoEquipo.objects.filter(
                semana_inicio=fila["semana_inicio"],
                trabajador=fila["trabajador"],
                dia=fila["dia"],
            ).first() or TurnoEquipo(
                semana_inicio=fila["semana_inicio"],
                trabajador=fila["trabajador"],
                dia=fila["dia"],
            )
            turno.entrada = fila["entrada"]
            turno.salida = fila["salida"]
            turno.es_libre = fila["es_libre"]
            turno.save()
            guardadas += 1
        except Exception as exc:  # noqa: BLE001
            logger.exception("Error guardando turno %s", fila)
            if on_error:
                on_error(f"{fila.get('trabajador')} {fila.get('dia')}: {exc}")
    if guardadas == 0 and filas:
        raise ImportacionError("No se pudo guardar ningún turno.")
    if on_ok:
        on_ok(guardadas)
    return guardadas
