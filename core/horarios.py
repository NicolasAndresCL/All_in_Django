"""
core/horarios.py — Lógica pura de cálculo de horarios (sin dependencias de Django).

Portado de all_in_one/core/horarios_logic.py. Es la fuente de verdad para el cálculo
de horas de turno y la semana de inicio; lo usan los modelos/serializers de turnos.
"""

from datetime import date, datetime, time, timedelta

DIAS_ORDEN = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
TRABAJADORES = ["Manu", "Jorge", "Babi", "Nico"]

DIAS_CHOICES = [(d, d) for d in DIAS_ORDEN]
TRABAJADORES_CHOICES = [(t, t) for t in TRABAJADORES]


def get_semana_inicio(fecha: date) -> date:
    """Lunes de la semana de `fecha`."""
    return fecha - timedelta(days=fecha.weekday())


def ordenar_horario(filas: list[dict]) -> list[dict]:
    """Ordena filas de horario por **día** (Lunes→Domingo) y, dentro de cada día, por
    **hora de entrada**. Las filas sin entrada (día libre) quedan al final de su día.

    Fuente de verdad del orden al imprimir/exportar horarios. Cada fila es un dict con
    al menos `dia` (str) y `entrada` (datetime.time | None).
    """
    def _clave(r):
        dia = DIAS_ORDEN.index(r["dia"]) if r.get("dia") in DIAS_ORDEN else len(DIAS_ORDEN)
        entrada = r.get("entrada")
        # `entrada is None` empuja los días libres al final del día; `entrada or time.min`
        # da una hora comparable (time es truthy en py3, incluso medianoche).
        return (dia, entrada is None, entrada or time.min)

    return sorted(filas, key=_clave)


def hora_a_decimal(h_str):
    """'HH:MM' → decimal. Horas < 8 se consideran del día siguiente (01:00 → 25.0)."""
    if not h_str or h_str == "LIBRE":
        return None
    hh, mm = map(int, str(h_str).split(":"))
    dec = hh + mm / 60
    if hh < 8:
        dec += 24
    return dec


def calcular_horas_turno(dia: str, hora_in: time, hora_out: time):
    """(bruto, neto, extra) de un turno. Maneja turnos que cruzan medianoche."""
    dt_i = datetime.combine(datetime.today(), hora_in)
    dt_o = datetime.combine(datetime.today(), hora_out)
    if hora_out < hora_in:
        dt_o += timedelta(days=1)
    bruto = (dt_o - dt_i).total_seconds() / 3600
    neto = max(0, bruto - 1) if bruto > 1 else bruto
    if dia == "Domingo":
        extra = bruto
    elif dia == "Sábado" and hora_out < hora_in:
        medianoche = datetime.combine(dt_o.date(), time(0, 0))
        limite_03 = datetime.combine(dt_o.date(), time(3, 0))
        extra = min(3.0, (min(dt_o, limite_03) - medianoche).total_seconds() / 3600)
    else:
        extra = 0
    return round(bruto, 2), round(neto, 2), round(extra, 2)
