"""
charts.py — Figuras Plotly del dashboard de Tareas (funciones puras, sin UI).

Extraído de `streamlit_ui/views/tareas.py::construir_figuras` para que sea importable
sin ningún framework de UI (los tests tampoco lo necesitan). La vista de NiceGUI las
dibuja con `ui.plotly`.
"""

import pandas as pd
import plotly.express as px


def construir_figuras(resumen: dict, template: str = "plotly_dark") -> dict:
    """
    Construye las 6 figuras Plotly del dashboard a partir del resumen de la API.

    Devuelve un dict con las claves: jerarquia, esfuerzo, intensidad, semanal,
    dia_semana, acumulado. Las que dependen de datos que podrían faltar
    (jerarquia, intensidad, acumulado) valen None si no hay datos.
    """
    figs: dict = {}

    df_t = pd.DataFrame(resumen["por_tarea"])
    if not df_t.empty:
        fig = px.sunburst(df_t, path=["proyecto", "tarea"], values="horas",
                          color_discrete_sequence=px.colors.qualitative.Pastel, template=template)
        fig.update_layout(margin=dict(t=10, l=0, r=0, b=0), height=350)
        figs["jerarquia"] = fig
    else:
        figs["jerarquia"] = None

    df_p = pd.DataFrame(resumen["por_proyecto"]).sort_values("horas")
    fig = px.bar(df_p, x="horas", y="proyecto", orientation="h",
                 color="horas", color_continuous_scale="Blues", template=template)
    fig.update_layout(height=350, showlegend=False)
    figs["esfuerzo"] = fig

    df_dia = pd.DataFrame(resumen["por_dia"])
    if not df_dia.empty:
        df_dia["fecha"] = pd.to_datetime(df_dia["fecha"])
        fig = px.area(df_dia, x="fecha", y="horas",
                      color_discrete_sequence=["#0e639c"], template=template)
        fig.update_layout(height=300)
        figs["intensidad"] = fig

        df_cum = df_dia.sort_values("fecha").copy()
        df_cum["acumuladas"] = df_cum["horas"].cumsum()
        fig = px.line(df_cum, x="fecha", y="acumuladas",
                      color_discrete_sequence=["#2ecc71"], template=template)
        fig.update_traces(fill="tozeroy", fillcolor="rgba(46,204,113,0.15)")
        fig.update_layout(height=300, yaxis_title="Horas acumuladas")
        figs["acumulado"] = fig
    else:
        figs["intensidad"] = figs["acumulado"] = None

    fig = px.bar(pd.DataFrame(resumen["por_semana"]), x="semana", y="horas",
                 color_discrete_sequence=["#0e639c"], template=template)
    fig.update_layout(height=300)
    figs["semanal"] = fig

    fig = px.bar(pd.DataFrame(resumen["por_dia_semana"]), x="dia", y="horas",
                 color="horas", color_continuous_scale="Teal", template=template)
    fig.update_layout(height=300, showlegend=False, xaxis_title=None)
    figs["dia_semana"] = fig

    return figs
