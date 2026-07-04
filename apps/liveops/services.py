"""
apps/liveops/services.py — Importación de turnos de equipo desde CSV/Excel.

Portado de all_in_one/core/liveops_import.py y adaptado al ORM de Django.
Mapea agentes a Babi/Jorge/Manu/Nico, deriva semana/día desde la fecha y deja que
el modelo calcule bruto/neto/extra al guardar. `guardar_turnos` admite callbacks
(`on_ok` / `on_error`) para desacoplar la lógica de la vista.
"""

import re
import unicodedata
from datetime import datetime, time
from typing import Callable

import pandas as pd

from core.exceptions import ArchivoInvalidoError, ImportacionError
from core.horarios import TRABAJADORES, get_semana_inicio
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

    Devuelve (filas, resumen, errores). Cada fila es un dict listo para
    update_or_create: semana_inicio(date), trabajador, dia, entrada(time|None),
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

    filas, errores = [], []
    for idx, r in df.iterrows():
        nfila = idx + 2  # +1 base-1, +1 encabezado
        raw = r[c_trab] if c_trab else r[c_acr]
        if raw is None or (isinstance(raw, float) and pd.isna(raw)):
            errores.append(f"Fila {nfila}: sin agente.")
            continue
        if pd.isna(r[c_fecha]):
            errores.append(f"Fila {nfila}: sin fecha.")
            continue
        try:
            fecha = pd.to_datetime(r[c_fecha]).date()
        except Exception:  # noqa: BLE001
            errores.append(f"Fila {nfila}: fecha inválida ({r[c_fecha]!r}).")
            continue

        from core.horarios import DIAS_ORDEN
        trab = normalizar_trabajador(raw)
        semana = get_semana_inicio(fecha)
        dia = DIAS_ORDEN[fecha.weekday()]
        estado = _norm(r[c_est]) if c_est else ""
        ent = parse_hora(r[c_ent]) if c_ent else None
        sal = parse_hora(r[c_sal]) if c_sal else None
        es_libre = estado == "libre" or ent is None or sal is None

        filas.append({
            "semana_inicio": semana,
            "trabajador": trab,
            "dia": dia,
            "entrada": None if es_libre else ent,
            "salida": None if es_libre else sal,
            "es_libre": es_libre,
        })

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
            TurnoEquipo.objects.update_or_create(
                semana_inicio=fila["semana_inicio"],
                trabajador=fila["trabajador"],
                dia=fila["dia"],
                defaults={
                    "entrada": fila["entrada"],
                    "salida": fila["salida"],
                    "es_libre": fila["es_libre"],
                },
            )
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
