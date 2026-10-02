"""Tests de la capa de ciencia de datos de Tareas: pandas, scikit-learn y seaborn.

Lógica pura sobre DataFrames construidos a mano (sin BD), salvo los de API.
"""

from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from . import analitica, informe
from .models import Registro
from .services import calcular_resumen, registros_a_frame


def _frame(filas: list[tuple]) -> pd.DataFrame:
    """[(fecha, proyecto, horas)] → el mismo DataFrame que produce `registros_a_frame`."""
    return registros_a_frame(
        [Registro(fecha=f, proyecto=p, tarea="t", duracion=timedelta(hours=h)) for f, p, h in filas]
    )


LUNES = date(2026, 1, 5)


def _semanas(horas_por_semana: list[float]) -> pd.DataFrame:
    """Una tarea el lunes de cada semana con las horas dadas (0 = semana sin registros)."""
    return _frame([(LUNES + timedelta(weeks=i), "P", h) for i, h in enumerate(horas_por_semana) if h])


# ─── registros_a_frame ───────────────────────────────────────────────────────
def test_registros_a_frame_tipa_columnas():
    df = _frame([(date(2026, 1, 1), "A", 1.5)])
    assert list(df.columns) == ["fecha", "proyecto", "tarea", "horas"]
    assert pd.api.types.is_datetime64_any_dtype(df["fecha"])
    assert df["horas"].iloc[0] == 1.5


def test_registros_a_frame_vacio_conserva_columnas():
    df = registros_a_frame([])
    assert df.empty and list(df.columns) == ["fecha", "proyecto", "tarea", "horas"]


@pytest.mark.django_db
def test_registros_a_frame_desde_queryset_usa_values_list():
    Registro.objects.create(fecha=date(2026, 1, 1), proyecto="A", tarea="x", duracion=timedelta(minutes=90))
    df = registros_a_frame(Registro.objects.all())
    assert df["horas"].tolist() == [1.5]


def test_resumen_devuelve_tipos_nativos_serializables():
    """`numpy.int64` no es JSON-serializable: el contrato exige int/float de Python."""
    regs = [Registro(fecha=date(2026, 1, 1), proyecto="A", tarea="x", duracion=timedelta(hours=2))]
    res = calcular_resumen(regs, date(2026, 1, 1))
    assert type(res["tareas"]) is int and type(res["proyectos"]) is int
    assert all(type(d["horas"]) is float for d in res["por_proyecto"] + res["por_dia_semana"])


# ─── serie_semanal / tendencia (LinearRegression) ────────────────────────────
def test_serie_semanal_rellena_semanas_vacias_con_cero():
    serie = analitica.serie_semanal(_semanas([5, 0, 0, 7]))
    assert serie.tolist() == [5.0, 0.0, 0.0, 7.0]


def test_tendencia_none_con_pocas_semanas():
    assert analitica.tendencia_semanal(_semanas([1, 2, 3])) is None
    assert analitica.tendencia_semanal(_frame([])) is None


def test_tendencia_recupera_una_recta_exacta():
    t = analitica.tendencia_semanal(_semanas([10, 12, 14, 16, 18]))
    assert t["pendiente"] == pytest.approx(2.0)
    assert t["r2"] == pytest.approx(1.0)
    assert t["proyeccion"] == pytest.approx(20.0)
    assert t["direccion"] == "sube"
    assert [p["ajustada"] for p in t["ajuste"]] == pytest.approx([10, 12, 14, 16, 18])


def test_tendencia_a_la_baja_no_proyecta_horas_negativas():
    t = analitica.tendencia_semanal(_semanas([12, 9, 6, 3]))
    assert t["direccion"] == "baja"
    assert t["proyeccion"] == 0.0


def test_tendencia_cuenta_las_pausas():
    """Una pausa de semanas vacías arrastra la pendiente: si se omitieran (en vez de
    contarlas como 0) la serie sería [10, 10, 10] y la tendencia, "estable"."""
    assert analitica.tendencia_semanal(_semanas([10, 10, 10, 10]))["direccion"] == "estable"
    con_pausa = analitica.tendencia_semanal(_semanas([10, 10, 0, 0, 0, 10]))
    assert con_pausa["semanas"] == 6
    assert con_pausa["pendiente"] == pytest.approx(-15 / 17.5, abs=0.01)
    assert con_pausa["direccion"] == "baja"


# ─── dias_atipicos (IsolationForest) ─────────────────────────────────────────
def _dias_normales(n: int = 30) -> list[tuple]:
    rnd = np.random.default_rng(1)
    return [(LUNES + timedelta(days=i), "P", float(h)) for i, h in enumerate(rnd.normal(8, 0.5, n).round(2))]


def test_atipicos_vacio_con_pocos_dias():
    assert analitica.dias_atipicos(_frame(_dias_normales(analitica.MIN_DIAS - 1))) == []


def test_atipicos_detecta_el_dia_extremo_y_explica_por_que():
    filas = [*_dias_normales(), (LUNES + timedelta(days=40), "P", 22.0)]
    atipicos = analitica.dias_atipicos(_frame(filas))
    assert atipicos, "un día de 22 h entre días de ~8 h debe salir"
    peor = atipicos[0]                               # ordenados del más raro al menos
    assert peor["fecha"] == (LUNES + timedelta(days=40)).isoformat()
    assert peor["motivo"] == "más horas de lo habitual"
    assert peor["puntaje"] < 0


def test_atipicos_es_deterministico():
    df = _frame([*_dias_normales(), (LUNES + timedelta(days=40), "P", 22.0)])
    assert analitica.dias_atipicos(df) == analitica.dias_atipicos(df)


def test_atipicos_marca_una_fraccion_acotada():
    """El fallo que motivó `CONTAMINACION`: con "auto" se marcaba el 28 % de los días."""
    df = _frame(_dias_normales(100))
    assert len(analitica.dias_atipicos(df)) <= 0.1 * 100


def test_calcular_analitica_declara_requisitos():
    res = analitica.calcular_analitica(_frame([]))
    assert res == {"tendencia": None, "atipicos": [],
                   "requisitos": {"min_semanas": analitica.MIN_SEMANAS, "min_dias": analitica.MIN_DIAS}}


# ─── informe PDF (seaborn) ───────────────────────────────────────────────────
def test_graficos_son_png():
    df = _semanas([3, 5, 0, 8, 9])
    for imagen in (informe.grafico_semanal(df, analitica.tendencia_semanal(df)),
                   informe.grafico_proyectos(df), informe.mapa_calor(df)):
        assert imagen.read(8) == b"\x89PNG\r\n\x1a\n"


def test_graficos_none_sin_datos():
    vacio = _frame([])
    assert informe.grafico_semanal(vacio, None) is None
    assert informe.grafico_proyectos(vacio) is None
    assert informe.mapa_calor(vacio) is None


def test_grafico_proyectos_pliega_en_otros_y_trunca_nombres():
    """Más de TOP_PROYECTOS no inventa colores: el resto va a "Otros"."""
    filas = [(LUNES, f"Proyecto con un nombre larguísimo número {i}", 1.0 + i) for i in range(12)]
    assert informe.grafico_proyectos(_frame(filas)).read(4) == b"\x89PNG"


def test_generar_informe_pdf_con_y_sin_datos():
    for df in (_frame([]), _semanas([3, 5, 0, 8, 9])):
        regs = [Registro(fecha=f.date(), proyecto=p, tarea="t", duracion=timedelta(hours=h))
                for f, p, h in df[["fecha", "proyecto", "horas"]].itertuples(index=False)]
        pdf = informe.generar_informe_pdf(df, calcular_resumen(regs), date(2026, 3, 1))
        assert pdf.startswith(b"%PDF-")


def test_informe_no_deja_figuras_en_el_registro_global_de_pyplot():
    """pyplot guarda las figuras en estado GLOBAL: en un worker de gunicorn, cada informe
    dejaría una figura viva (fuga). Se mira el registro, no el código: seaborn importa
    pyplot por su cuenta, así que "no importarlo" no es la garantía que importa."""
    from matplotlib import pyplot as plt

    df = _semanas([3, 5, 0, 8, 9])
    informe.generar_informe_pdf(df, calcular_resumen([]), date(2026, 3, 1))
    assert plt.get_fignums() == []


# ─── API ─────────────────────────────────────────────────────────────────────
@pytest.mark.django_db
def test_api_analitica(api):
    for i, h in enumerate([10, 12, 14, 16]):
        Registro.objects.create(fecha=LUNES + timedelta(weeks=i), proyecto="A", tarea="x",
                                duracion=timedelta(hours=h))
    Registro.objects.create(fecha=LUNES, proyecto="B", tarea="x", duracion=timedelta(hours=99))

    data = api.get("/api/tareas/analitica/?proyecto=A").data
    assert data["tendencia"]["pendiente"] == pytest.approx(2.0)   # respeta ?proyecto=
    assert data["atipicos"] == []


@pytest.mark.django_db
def test_api_informe_descarga_pdf(api):
    Registro.objects.create(fecha=LUNES, proyecto="A", tarea="x", duracion=timedelta(hours=2))
    resp = api.get("/api/tareas/informe/")
    assert resp.status_code == 200
    assert resp["Content-Type"] == "application/pdf"
    assert "attachment" in resp["Content-Disposition"]
    assert resp.content.startswith(b"%PDF-")
