"""Tests de construcción de los Gantt (sin runtime de UI)."""

from nicegui_ui.gantt import (
    COLORES_TRABAJADOR,
    generar_gantt,
    generar_gantt_equipo,
    hora_a_decimal,
    instante,
)
from nicegui_ui.plotly_tema import PALETA, PLANTILLA

H = 3_600_000  # una hora en ms (unidad de `x` en un eje `date`)

CLASES = [{"dia": "Lunes", "asignatura": "Mate", "entrada": "08:00:00",
           "salida": "10:00:00", "horas": 2.0}]
TURNOS = [{"dia": "Lunes", "entrada": "18:00:00", "salida": "23:00:00",
           "neto": 4.0, "es_libre": False},
          {"dia": "Martes", "entrada": None, "salida": None, "es_libre": True},
          {"dia": "Viernes", "entrada": "20:00:00", "salida": "02:00:00",
           "neto": 6.0, "es_libre": False}]


def test_hora_a_decimal():
    assert hora_a_decimal("09:30:00") == 9.5
    assert hora_a_decimal("01:00:00") == 25.0   # de madrugada → día siguiente
    assert hora_a_decimal(None) is None
    assert hora_a_decimal("LIBRE") is None


def test_instante_lleva_la_madrugada_al_dia_siguiente():
    assert instante(9.5).endswith("T09:30:00")
    assert instante(25.0) > instante(23.0)   # 01:00 (+1) va DESPUÉS de las 23:00


def test_gantt_personal_una_traza_por_categoria():
    fig = generar_gantt(CLASES, TURNOS, "2026-06-08")
    assert [t.name for t in fig.data] == ["_dias", "Santo Tomás", "PedidosYa"]
    _, estudio, trabajo = fig.data
    assert list(estudio.x) == [2 * H]
    # El libre se omite; el turno que cruza medianoche dura 6 h, no -18.
    assert list(trabajo.x) == [5 * H, 6 * H]
    assert list(trabajo.y) == ["Lun", "Vie"]


def test_gantt_personal_usa_eje_de_hora_real_y_la_plantilla():
    """El eje `date` es lo que hace ADAPTATIVOS los ticks: con 20 `tickvals` fijos las
    horas se apilaban por debajo de ~420 px."""
    fig = generar_gantt(CLASES, TURNOS)
    assert fig.layout.xaxis.type == "date"
    assert fig.layout.xaxis.tickvals is None
    assert fig.layout.xaxis.tickformat == "%H:%M"
    # Sin alto fijo: lo decide el contenedor por CSS según el ancho.
    assert fig.layout.height is None
    assert fig.layout.template.layout.colorway == tuple(PALETA)
    assert fig.layout.template.layout.font.color != "#2a3f5f"  # el azul marino de Plotly


def test_gantt_equipo_agrupa_por_trabajador_con_color_fijo():
    turnos = [
        {"trabajador": "Babi", "dia": "Lunes", "entrada": "13:00:00", "salida": "22:00:00",
         "neto": 8.0, "extra": 0.0, "es_libre": False},
        {"trabajador": "Nico", "dia": "Lunes", "entrada": "09:00:00", "salida": "18:00:00",
         "neto": 8.0, "extra": 0.0, "es_libre": False},
    ]
    fig = generar_gantt_equipo(turnos)
    assert {t.name for t in fig.data if t.showlegend is not False} == {"Babi", "Nico"}
    # El color sigue a la PERSONA, no a su posición: filtrar a una no repinta a otra.
    solo_nico = generar_gantt_equipo(turnos[1:])
    assert solo_nico.data[-1].marker.color == COLORES_TRABAJADOR["Nico"]
    assert fig.layout.barmode == "group"
    assert fig.layout.xaxis.type == "date"


def test_las_figuras_usan_la_plantilla_propia():
    assert generar_gantt([], []).layout.template is not None
    assert PLANTILLA == "aid"


def test_los_7_dias_existen_aunque_falten_bloques():
    """Una semana sin turnos el finde perdía Sáb y Dom del eje."""
    for fig in (generar_gantt(CLASES, []), generar_gantt_equipo([])):
        ancla = fig.data[0]
        assert ancla.name == "_dias" and ancla.showlegend is False
        assert list(ancla.y) == ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
