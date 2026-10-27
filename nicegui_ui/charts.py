"""
charts.py — Figuras Plotly del dashboard de Tareas (funciones puras, sin UI).

Importable sin ningún framework de UI (los tests tampoco lo necesitan); la vista de
NiceGUI las dibuja con `layout.grafico`. El aspecto (tinta, rejilla, leyenda, paleta)
lo pone la plantilla `aid` de `plotly_tema.py`: aquí solo va la FORMA de cada gráfico.

Las figuras NO fijan `height`: la altura la decide el contenedor por CSS según el ancho
(`aid-alto-*` en `tema.py`). Con alturas fijas en píxeles, en un móvil quedaban tiras
altas y flacas.

Decisiones de forma (skill `dataviz`):
  - `jerarquia`: TREEMAP en vez de sunburst. El sunburst ponía una rebanada por tarea en
    el anillo exterior —cientos— y no se leía a ningún tamaño. El treemap usa el área
    entera, y las colas se pliegan en "Otras"/"Otros proyectos".
  - `esfuerzo` y `dia_semana`: UNA serie → UN color. La escala de color por horas
    repetía la longitud de la barra y su colorbar se comía un tercio del ancho.
  - `intensidad`: calendario de actividad (heatmap semana × día) en vez de un área
    diaria con cientos de picos: deja ver hábitos (qué días, qué rachas) de un vistazo.
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from nicegui_ui.plotly_tema import (
    COLOR_OTROS,
    MAX_CATEGORIAS,
    PALETA,
    PLANTILLA,
    SECUENCIAL,
    truncar,
)

DIAS_CORTOS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
DIAS_LARGOS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

TOP_PROYECTOS = MAX_CATEGORIAS        # 7 con color propio + "Otros proyectos"
TOP_TAREAS = 5                        # por proyecto, el resto en "Otras (n)"
TOP_BARRAS = 10                       # filas de "Esfuerzo por proyecto"
SEMANAS_CALENDARIO = 26               # medio año: legible a 360 px

OTROS_PROYECTOS = "Otros proyectos"

COLOR_SERIE = PALETA[0]
RELLENO_SERIE = "rgba(57, 135, 229, 0.16)"


# ─── Plegado de colas ────────────────────────────────────────────────────────
def plegar_proyectos(por_tarea: list[dict], top: int = TOP_PROYECTOS,
                     top_tareas: int = TOP_TAREAS) -> pd.DataFrame:
    """`por_tarea` → DataFrame (proyecto, tarea, horas) con las colas plegadas.

    Los `top` proyectos con más horas conservan su nombre; el resto se suma en un único
    nodo "Otros proyectos". Dentro de cada proyecto, más allá de `top_tareas` las tareas
    se suman en "Otras (n)". Sin esto el treemap tenía un rectángulo por tarea.
    """
    df = pd.DataFrame(por_tarea, columns=["proyecto", "tarea", "horas"])
    if df.empty:
        return df
    totales = df.groupby("proyecto")["horas"].sum().sort_values(ascending=False)
    principales = list(totales.index[:top])
    resto = df[~df["proyecto"].isin(principales)]

    filas = []
    for proyecto in principales:
        tareas = df[df["proyecto"] == proyecto].sort_values("horas", ascending=False)
        filas += tareas.head(top_tareas)[["proyecto", "tarea", "horas"]].to_dict("records")
        cola = tareas.iloc[top_tareas:]
        if not cola.empty:
            filas.append({"proyecto": proyecto, "tarea": f"Otras ({len(cola)})",
                          "horas": float(cola["horas"].sum())})
    if not resto.empty:
        n = resto["proyecto"].nunique()
        filas.append({"proyecto": OTROS_PROYECTOS, "tarea": f"{n} proyectos",
                      "horas": float(resto["horas"].sum())})
    return pd.DataFrame(filas)


def colores_proyecto(proyectos: list[str]) -> dict[str, str]:
    """Color por ENTIDAD, en el orden fijo de la paleta; "Otros" siempre en gris."""
    reales = [p for p in proyectos if p != OTROS_PROYECTOS]
    mapa = {p: PALETA[i % MAX_CATEGORIAS] for i, p in enumerate(reales)}
    mapa[OTROS_PROYECTOS] = COLOR_OTROS
    return mapa


# ─── Figuras ─────────────────────────────────────────────────────────────────
def figura_jerarquia(por_tarea: list[dict]) -> go.Figure | None:
    df = plegar_proyectos(por_tarea)
    if df.empty:
        return None
    orden = list(dict.fromkeys(df["proyecto"]))
    # Raíz EXPLÍCITA: Plotly reserva igual una franja de cabecera para la raíz implícita;
    # con nombre propio esa franja dice algo (el total) en vez de quedar vacía.
    raiz = f"Todas las horas · {df['horas'].sum():.0f} h"
    fig = px.treemap(df, path=[px.Constant(raiz), "proyecto", "tarea"], values="horas",
                     color="proyecto", color_discrete_map=colores_proyecto(orden) | {"(?)": "rgba(0,0,0,0)"},
                     template=PLANTILLA)
    fig.update_traces(
        texttemplate="<b>%{label}</b><br>%{value:.1f} h",
        hovertemplate="<b>%{label}</b><br>%{value:.1f} h · %{percentRoot:.0%} del total<extra></extra>",
        marker=dict(line=dict(width=2, color="#0c1222"), cornerradius=4),
        tiling=dict(pad=2), pathbar=dict(visible=False), root=dict(color="rgba(0,0,0,0)"),
        maxdepth=3,
    )
    return fig


def figura_esfuerzo(por_proyecto: list[dict], top: int = TOP_BARRAS) -> go.Figure:
    df = pd.DataFrame(por_proyecto, columns=["proyecto", "horas"]).sort_values("horas", ascending=False)
    if len(df) > top:
        cola = df.iloc[top - 1:]
        df = pd.concat([df.iloc[: top - 1],
                        pd.DataFrame([{"proyecto": f"Otros ({len(cola)})",
                                       "horas": float(cola["horas"].sum())}])])
    df = df.iloc[::-1]  # la barra más larga arriba
    fig = go.Figure(go.Bar(
        x=df["horas"], y=[truncar(p) for p in df["proyecto"]], orientation="h",
        marker_color=COLOR_SERIE, customdata=df["proyecto"],
        hovertemplate="<b>%{customdata}</b><br>%{x:.1f} h<extra></extra>",
    ))
    fig.update_layout(template=PLANTILLA, showlegend=False,
                      xaxis=dict(title="Horas"), yaxis=dict(title=None))
    return fig


def calendario_actividad(por_dia: list[dict], semanas: int = SEMANAS_CALENDARIO):
    """Rejilla (7 días × `semanas`) de horas por día, terminando en el último registro.

    Devuelve (lunes_de_cada_semana, z[dia][semana], fechas[dia][semana]). Los días sin
    registro valen 0; los posteriores al último registro, None (hueco, no "cero horas").
    """
    if not por_dia:
        return [], [], []
    horas = {pd.Timestamp(d["fecha"]).date(): float(d["horas"]) for d in por_dia}
    ultimo = max(horas)
    lunes_final = ultimo - timedelta(days=ultimo.weekday())
    lunes = [lunes_final - timedelta(weeks=semanas - 1 - i) for i in range(semanas)]
    z, fechas = [], []
    for dia in range(7):
        fila_z, fila_f = [], []
        for inicio in lunes:
            f: date = inicio + timedelta(days=dia)
            fila_z.append(None if f > ultimo else horas.get(f, 0.0))
            fila_f.append(f"{DIAS_LARGOS[dia]} {f:%d-%m-%Y}")
        z.append(fila_z)
        fechas.append(fila_f)
    return lunes, z, fechas


def figura_calendario(por_dia: list[dict]) -> go.Figure | None:
    lunes, z, fechas = calendario_actividad(por_dia)
    if not lunes:
        return None
    fig = go.Figure(go.Heatmap(
        x=lunes, y=DIAS_CORTOS, z=z, customdata=fechas, colorscale=SECUENCIAL,
        xgap=2, ygap=2, hoverongaps=False, zmin=0,
        hovertemplate="%{customdata}<br><b>%{z:.1f} h</b><extra></extra>",
        # Escala secuencial → leyenda de escala obligatoria, pero HORIZONTAL y fina: la
        # vertical por defecto se llevaba un buen tramo del ancho en móvil.
        colorbar=dict(orientation="h", thickness=8, len=0.45, x=1, xanchor="right",
                      y=1.0, yanchor="bottom", title=dict(text="h/día", side="top"),
                      outlinewidth=0, tickfont=dict(size=10)),
    ))
    fig.update_layout(template=PLANTILLA,
                      xaxis=dict(type="date", tickformat="%b", showgrid=False, ticks=""),
                      yaxis=dict(autorange="reversed", showgrid=False, ticks=""))
    return fig


def figura_semanal(por_semana: list[dict]) -> go.Figure:
    df = pd.DataFrame(por_semana, columns=["semana", "horas"])
    fig = go.Figure(go.Bar(x=df["semana"], y=df["horas"], marker_color=COLOR_SERIE,
                           hovertemplate="%{x}<br><b>%{y:.1f} h</b><extra></extra>"))
    # Eje de CATEGORÍAS ("Sem 27"): Plotly pinta una etiqueta por barra y con 40 semanas
    # se apilaban en vertical. `nticks` deja que muestre una de cada N.
    fig.update_layout(template=PLANTILLA, showlegend=False,
                      xaxis=dict(title=None, nticks=10, tickangle=0), yaxis=dict(title="Horas"))
    return fig


def figura_dia_semana(por_dia_semana: list[dict]) -> go.Figure:
    df = pd.DataFrame(por_dia_semana, columns=["dia", "horas"])
    cortos = dict(zip(DIAS_LARGOS, DIAS_CORTOS, strict=True))
    fig = go.Figure(go.Bar(x=[cortos.get(d, d) for d in df["dia"]], y=df["horas"],
                           marker_color=COLOR_SERIE, customdata=df["dia"],
                           hovertemplate="%{customdata}<br><b>%{y:.1f} h</b><extra></extra>"))
    fig.update_layout(template=PLANTILLA, showlegend=False,
                      xaxis=dict(title=None), yaxis=dict(title="Horas"))
    return fig


def figura_acumulado(por_dia: list[dict]) -> go.Figure | None:
    df = pd.DataFrame(por_dia, columns=["fecha", "horas"])
    if df.empty:
        return None
    df = df.assign(fecha=pd.to_datetime(df["fecha"])).sort_values("fecha")
    df["acumuladas"] = df["horas"].cumsum()
    fig = go.Figure(go.Scatter(
        x=df["fecha"], y=df["acumuladas"], mode="lines", line=dict(color=COLOR_SERIE, width=2),
        fill="tozeroy", fillcolor=RELLENO_SERIE,
        hovertemplate="%{x|%d-%m-%Y}<br><b>%{y:.0f} h</b> acumuladas<extra></extra>",
    ))
    fig.update_layout(template=PLANTILLA, showlegend=False, hovermode="x",
                      xaxis=dict(title=None, showspikes=True, spikemode="across",
                                 spikethickness=1, spikedash="solid", spikecolor="#8A93A8"),
                      yaxis=dict(title="Horas acumuladas"))
    return fig


def construir_figuras(resumen: dict) -> dict:
    """
    Las 6 figuras del dashboard a partir del resumen de la API.

    Claves: jerarquia, esfuerzo, intensidad, semanal, dia_semana, acumulado. Las que
    dependen de datos que podrían faltar (jerarquia, intensidad, acumulado) valen None.
    """
    return {
        "jerarquia": figura_jerarquia(resumen["por_tarea"]),
        "esfuerzo": figura_esfuerzo(resumen["por_proyecto"]),
        "intensidad": figura_calendario(resumen["por_dia"]),
        "semanal": figura_semanal(resumen["por_semana"]),
        "dia_semana": figura_dia_semana(resumen["por_dia_semana"]),
        "acumulado": figura_acumulado(resumen["por_dia"]),
    }


# La serie real conserva el azul del resto del dashboard (slot 1) y la recta de
# tendencia lleva el slot 2: pareja validada también con CVD.
COLOR_REAL, COLOR_TENDENCIA = PALETA[0], PALETA[1]


def figura_tendencia(tendencia: dict | None) -> go.Figure | None:
    """Barras de horas por semana + la recta de `LinearRegression` de `tareas/analitica/`.

    Dibuja el `ajuste` que ya calculó la API (no reajusta nada en el cliente). Dos series
    → leyenda visible. `None` si la API no devolvió tendencia (pocas semanas).
    """
    if not tendencia or not tendencia.get("ajuste"):
        return None
    df = pd.DataFrame(tendencia["ajuste"]).assign(semana=lambda d: pd.to_datetime(d["semana"]))
    fig = go.Figure([
        go.Bar(x=df["semana"], y=df["horas"], name="Horas reales", marker_color=COLOR_REAL,
               hovertemplate="%{y:.1f} h<extra>Horas reales</extra>"),
        go.Scatter(x=df["semana"], y=df["ajustada"], name="Tendencia lineal", mode="lines",
                   line=dict(color=COLOR_TENDENCIA, width=2),
                   hovertemplate="%{y:.1f} h<extra>Tendencia</extra>"),
    ])
    fig.update_layout(template=PLANTILLA, hovermode="x unified",
                      yaxis_title="Horas", xaxis_title="Semana (lunes)")
    return fig
