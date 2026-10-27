"""Tests de las figuras del dashboard de Tareas (charts.py, sin runtime de UI)."""

import pytest

from nicegui_ui import plotly_tema
from nicegui_ui.charts import (
    MAX_ETIQUETAS_SEMANA,
    OTROS_PROYECTOS,
    calendario_actividad,
    colores_proyecto,
    construir_figuras,
    etiquetas_semana,
    figura_esfuerzo,
    figura_tendencia,
    plegar_proyectos,
)

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
    assert figs["jerarquia"].data[0].type == "treemap"
    assert figs["intensidad"].data[0].type == "heatmap"


def test_ninguna_figura_fija_altura_y_todas_usan_la_plantilla():
    """La altura la pone el CSS según el ancho; un `height` en px volvería a dejar
    tiras altas y flacas en móvil."""
    for clave, fig in construir_figuras(RESUMEN).items():
        assert fig.layout.height is None, clave
        assert fig.layout.template.layout.paper_bgcolor == "rgba(0,0,0,0)", clave


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


@pytest.mark.parametrize("clave", ["esfuerzo", "dia_semana"])
def test_una_serie_un_color_y_sin_colorbar_redundante(clave):
    """La escala de color por horas repetía la longitud de la barra y su colorbar se
    comía un tercio del ancho (skill dataviz: 'value-ramp on nominal categories')."""
    fig = construir_figuras(RESUMEN)[clave]
    assert fig.data[0].marker.color == plotly_tema.PALETA[0]
    assert fig.layout.coloraxis.colorbar.to_plotly_json() == {}


@pytest.mark.parametrize("n", [1, 6, 7, 40, 104])
def test_el_eje_semanal_nunca_rotula_mas_del_tope_y_siempre_la_ultima(n):
    """Eje de categorías: Plotly no oculta las etiquetas que se pisan, así que el tope
    lo pone el código. La última semana (la en curso) siempre lleva rótulo."""
    semanas = [f"Sem {i}" for i in range(1, n + 1)]
    vals, textos = etiquetas_semana(semanas)
    assert 1 <= len(vals) <= MAX_ETIQUETAS_SEMANA
    assert vals[-1] == semanas[-1]
    assert textos[-1] == f"S{n}"


def test_la_figura_semanal_usa_las_etiquetas_cortas():
    semanas = [{"semana": f"Sem {i}", "horas": 1.0} for i in range(3, 43)]
    eje = construir_figuras({**RESUMEN, "por_semana": semanas})["semanal"].layout.xaxis
    assert eje.tickmode == "array"
    assert len(eje.tickvals) <= MAX_ETIQUETAS_SEMANA
    assert all(t.startswith("S") and " " not in t for t in eje.ticktext)


# ─── plegado de colas ────────────────────────────────────────────────────────
def _muchas_tareas(n_proyectos: int, n_tareas: int) -> list[dict]:
    return [{"proyecto": f"P{p}", "tarea": f"t{t}", "horas": float(n_proyectos - p + t)}
            for p in range(n_proyectos) for t in range(n_tareas)]


def test_el_treemap_pliega_proyectos_y_tareas_de_la_cola():
    df = plegar_proyectos(_muchas_tareas(12, 9))
    proyectos = list(dict.fromkeys(df["proyecto"]))
    assert len(proyectos) == plotly_tema.MAX_CATEGORIAS + 1
    assert proyectos[-1] == OTROS_PROYECTOS
    # 5 tareas + "Otras (4)" por proyecto principal: nunca un rectángulo por tarea.
    assert (df.groupby("proyecto").size().drop(OTROS_PROYECTOS) == 6).all()
    assert "Otras (4)" in set(df["tarea"])
    # Plegar no pierde horas.
    assert df["horas"].sum() == pytest.approx(sum(r["horas"] for r in _muchas_tareas(12, 9)))


def test_colores_por_entidad_y_otros_en_gris():
    mapa = colores_proyecto(["A", "B", OTROS_PROYECTOS])
    assert mapa["A"] == plotly_tema.PALETA[0]
    assert mapa["B"] == plotly_tema.PALETA[1]
    assert mapa[OTROS_PROYECTOS] == plotly_tema.COLOR_OTROS


def test_esfuerzo_trunca_etiquetas_y_conserva_el_nombre_en_el_tooltip():
    largo = "Proyecto con un nombre larguísimo de verdad"
    fig = figura_esfuerzo([{"proyecto": largo, "horas": 3.0}])
    assert fig.data[0].y[0].endswith("…") and len(fig.data[0].y[0]) <= 18
    assert fig.data[0].customdata[0] == largo


def test_esfuerzo_agrupa_la_cola_en_otros():
    filas = [{"proyecto": f"P{i}", "horas": float(20 - i)} for i in range(15)]
    fig = figura_esfuerzo(filas, top=10)
    assert len(fig.data[0].y) == 10
    assert fig.data[0].y[0] == "Otros (6)"  # va abajo: la más larga arriba


# ─── calendario de actividad ─────────────────────────────────────────────────
def test_calendario_rejilla_7_por_semanas_y_huecos_despues_del_ultimo_dia():
    lunes, z, fechas = calendario_actividad(
        [{"fecha": "2026-07-01", "horas": 4.0}, {"fecha": "2026-06-22", "horas": 1.5}], semanas=3)
    assert len(z) == 7 and all(len(fila) == 3 for fila in z)
    assert str(lunes[-1]) == "2026-06-29"
    assert z[2][-1] == 4.0           # miércoles 1-jul
    assert z[0][1] == 1.5            # lunes 22-jun
    assert z[3][-1] is None          # jueves 2-jul: después del último registro
    assert z[1][0] == 0.0            # día sin registro = 0 h, no hueco
    assert fechas[2][-1] == "Miércoles 01-07-2026"


def test_calendario_vacio():
    assert calendario_actividad([]) == ([], [], [])


# ─── tendencia ───────────────────────────────────────────────────────────────
def test_figura_tendencia_dibuja_real_y_recta_con_leyenda():
    tendencia = {"ajuste": [{"semana": "2026-06-01", "horas": 10.0, "ajustada": 9.5},
                            {"semana": "2026-06-08", "horas": 12.0, "ajustada": 12.5}]}
    fig = figura_tendencia(tendencia)
    assert [t.name for t in fig.data] == ["Horas reales", "Tendencia lineal"]
    assert list(fig.data[1].y) == [9.5, 12.5]
    # Leyenda horizontal (de la plantilla): la vertical se comía el ancho en móvil.
    assert fig.layout.template.layout.legend.orientation == "h"


def test_figura_tendencia_none_sin_datos():
    assert figura_tendencia(None) is None
    assert figura_tendencia({"ajuste": []}) is None


# ─── plantilla y configuración ───────────────────────────────────────────────
def test_config_reduce_la_barra_y_conserva_la_descarga():
    cfg = plotly_tema.config("x")
    assert cfg["displayModeBar"] == "hover"
    assert "lasso2d" in cfg["modeBarButtonsToRemove"]
    assert "toImage" not in cfg["modeBarButtonsToRemove"]
    assert cfg["toImageButtonOptions"]["filename"] == "x"
    assert cfg["responsive"] is True


def test_truncar():
    assert plotly_tema.truncar("corto") == "corto"
    assert plotly_tema.truncar("x" * 30, 10) == "x" * 9 + "…"
