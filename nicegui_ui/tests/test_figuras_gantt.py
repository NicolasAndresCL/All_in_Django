"""Tests de construcción de los Gantt (sin runtime de Streamlit)."""

from nicegui_ui.gantt import generar_gantt, generar_gantt_equipo, hora_a_decimal


def test_hora_a_decimal():
    assert hora_a_decimal("09:30:00") == 9.5
    assert hora_a_decimal("01:00:00") == 25.0   # de madrugada → día siguiente
    assert hora_a_decimal(None) is None
    assert hora_a_decimal("LIBRE") is None


def test_gantt_personal_incluye_estudio_y_trabajo():
    clases = [{"dia": "Lunes", "asignatura": "Mate", "entrada": "08:00:00",
               "salida": "10:00:00", "horas": 2.0}]
    turnos = [{"dia": "Lunes", "entrada": "18:00:00", "salida": "23:00:00",
               "neto": 4.0, "es_libre": False},
              {"dia": "Martes", "entrada": None, "salida": None, "es_libre": True}]
    fig = generar_gantt(clases, turnos, "2026-06-08")
    # 1 clase + 1 turno activo (el libre se omite) + 2 trazas de leyenda = 4.
    assert len(fig.data) == 4


def test_gantt_equipo_agrupa_por_trabajador():
    turnos = [
        {"trabajador": "Babi", "dia": "Lunes", "entrada": "13:00:00", "salida": "22:00:00",
         "neto": 8.0, "extra": 0.0, "es_libre": False},
        {"trabajador": "Nico", "dia": "Lunes", "entrada": "09:00:00", "salida": "18:00:00",
         "neto": 8.0, "extra": 0.0, "es_libre": False},
    ]
    fig = generar_gantt_equipo(turnos)
    nombres = {t.name for t in fig.data}
    assert nombres == {"Babi", "Nico"}
