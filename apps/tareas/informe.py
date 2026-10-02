"""
apps/tareas/informe.py — Informe PDF de Registro de Tareas con gráficos seaborn.

La UI dibuja con Plotly (interactivo, en el navegador). Un PDF necesita lo contrario:
imágenes ESTÁTICAS renderizadas en el servidor. Ahí entra seaborn, y en concreto su
interfaz declarativa **`seaborn.objects`**: el gráfico se describe (`Plot(datos, x, y)
.add(marca).scale(...).label(...)`) en vez de dibujarse paso a paso sobre unos ejes.

Reglas de diseño (skill `dataviz`): una serie = un color y sin leyenda; dos series =
leyenda; tendencia en un segundo tono de la paleta categórica validada; rejilla
recesiva; magnitud con una rampa secuencial de UN solo tono (mapa de calor).

Trampas que condicionan el código:

- **Nunca `pyplot`.** `matplotlib.pyplot` guarda figuras en un estado GLOBAL del
  proceso; en un worker de gunicorn que atiende peticiones sin parar, una figura sin
  cerrar es una fuga de memoria. Se usa `matplotlib.figure.Figure` directamente (sin
  backend interactivo ni registro global) y `Plot.on(fig)`.
- **Fuentes core de fpdf2 = latin-1**: el texto pasa por `_txt` (como en
  `core/horarios_export.py`), o un "Sesión" con un carácter fuera de rango rompe el PDF.
"""

from datetime import date
from io import BytesIO

import pandas as pd
import seaborn as sns
import seaborn.objects as so
from fpdf import FPDF
from matplotlib import rc_context
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from PIL import Image

from core.horarios_export import _txt

from .analitica import dias_atipicos, serie_semanal, tendencia_semanal
from .services import DIAS_ES

# Paleta de referencia de la skill dataviz (modo claro: el PDF se imprime en blanco).
AZUL, NARANJA = "#2a78d6", "#eb6834"
TINTA, TINTA_SUAVE, REJILLA = "#0b0b0b", "#52514e", "#e6e6e6"
TOP_PROYECTOS = 8          # el resto se pliega en "Otros" (no se inventan más tonos)
SEMANAS_MAPA = 12          # ventana del mapa de calor
LARGO_ETIQUETA = 32        # nombres de proyecto más largos se truncan con "…"
DPI = 150

TEMA = {
    **sns.axes_style("whitegrid"),
    "axes.edgecolor": REJILLA,
    "grid.color": REJILLA,
    "axes.labelcolor": TINTA_SUAVE,
    "xtick.color": TINTA_SUAVE,
    "ytick.color": TINTA_SUAVE,
    "text.color": TINTA,
    "font.size": 9,
}


def _png(fig: Figure) -> BytesIO:
    buffer = BytesIO()
    fig.savefig(buffer, format="png", dpi=DPI, bbox_inches="tight", facecolor="white")
    buffer.seek(0)
    return buffer


def grafico_semanal(df: pd.DataFrame, tendencia: dict | None) -> BytesIO | None:
    """Barras de horas por semana + la recta de `LinearRegression` (si hay tendencia).

    Recibe la tendencia ya ajustada (`analitica.tendencia_semanal`) para no reentrenar
    el modelo: la misma recta sale en el gráfico y en la nota de texto.
    """
    if tendencia is not None:
        datos = pd.DataFrame(tendencia["ajuste"])
    else:
        semanal = serie_semanal(df)
        if semanal.empty:
            return None
        datos = semanal.reset_index().assign(semana=lambda d: d["semana"].dt.strftime("%Y-%m-%d"))
    datos = datos.assign(etiqueta=pd.to_datetime(datos["semana"]).dt.strftime("%d-%m"))

    fig = Figure(figsize=(7.5, 3))
    plot = (
        so.Plot(datos, x="etiqueta", y="horas")
        .add(so.Bar(color=AZUL, alpha=0.9, edgewidth=0))
        .label(x="Semana (lunes)", y="Horas")
        .theme(TEMA)
        .on(fig)
    )
    leyenda = [Patch(color=AZUL, label="Horas reales")]
    if tendencia is not None:
        plot = plot.add(so.Line(color=NARANJA, linewidth=2), y="ajustada")
        leyenda.append(Line2D([], [], color=NARANJA, linewidth=2, label="Tendencia lineal"))
    plot.plot()
    ax = fig.axes[0]
    ax.tick_params(axis="x", labelrotation=60, labelsize=7)
    if len(leyenda) > 1:
        ax.legend(handles=leyenda, frameon=False, loc="upper left")
    return _png(fig)


def grafico_proyectos(df: pd.DataFrame) -> BytesIO | None:
    """Horas por proyecto (top N + "Otros"), barras horizontales de un solo tono."""
    if df.empty:
        return None
    por_proyecto = df.groupby("proyecto")["horas"].sum().sort_values(ascending=False)
    top = por_proyecto.head(TOP_PROYECTOS)
    resto = por_proyecto.iloc[TOP_PROYECTOS:].sum()
    if resto > 0:
        top = pd.concat([top, pd.Series({"Otros": resto})])
    datos = top.rename("horas").rename_axis("proyecto").reset_index()
    largos = datos["proyecto"].str.len() > LARGO_ETIQUETA
    datos.loc[largos, "proyecto"] = datos.loc[largos, "proyecto"].str[: LARGO_ETIQUETA - 1] + "…"

    fig = Figure(figsize=(7.5, 0.35 * len(datos) + 0.8))
    (
        so.Plot(datos, x="horas", y="proyecto")
        .add(so.Bar(color=AZUL, alpha=0.9, edgewidth=0), orient="y")
        .label(x="Horas", y=None)
        .theme(TEMA)
        .on(fig)
        .plot()
    )
    return _png(fig)


def mapa_calor(df: pd.DataFrame) -> BytesIO | None:
    """Horas por día de la semana × semana (últimas `SEMANAS_MAPA`), rampa de un tono."""
    if df.empty:
        return None
    lunes = df["fecha"] - pd.to_timedelta(df["fecha"].dt.weekday, unit="D")
    tabla = (
        df.assign(semana=lunes, dia=df["fecha"].dt.weekday)
        .pivot_table(index="dia", columns="semana", values="horas", aggfunc="sum", fill_value=0.0)
        .reindex(range(7), fill_value=0.0)
        .iloc[:, -SEMANAS_MAPA:]
    )
    tabla = tabla.set_axis(DIAS_ES, axis=0).set_axis(tabla.columns.strftime("%d-%m"), axis=1)

    # sns.heatmap es de la API clásica (no de seaborn.objects): no recibe `.theme()`, así
    # que el mismo tema se aplica con un rc_context local (sin tocar el estado global).
    with rc_context(TEMA):
        fig = Figure(figsize=(7.5, 2.8))
        ax = fig.subplots()
        sns.heatmap(tabla, ax=ax, cmap="Blues", linewidths=2, linecolor="white",
                    cbar_kws={"label": "Horas"}, annot=tabla.shape[1] <= 8, fmt=".0f")
        ax.set(xlabel="Semana (lunes)", ylabel=None)
        ax.tick_params(length=0)
        ax.collections[0].colorbar.ax.tick_params(length=0)
        ax.tick_params(axis="x", labelrotation=60, labelsize=7)
    return _png(fig)


def generar_informe_pdf(df: pd.DataFrame, resumen: dict, hoy: date | None = None) -> bytes:
    """PDF de una o dos páginas: KPIs, tendencia, proyectos, mapa de calor y atípicos."""
    hoy = hoy or date.today()
    tendencia = tendencia_semanal(df)
    atipicos = dias_atipicos(df)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 9, _txt("Informe de Registro de Tareas"), new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(82, 81, 78)
    pdf.cell(0, 6, _txt(f"Generado el {hoy.isoformat()}"), new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)

    kpis = [
        ("Registros", resumen["tareas"]),
        ("Proyectos", resumen["proyectos"]),
        ("Horas", f"{resumen['horas_total']:.1f}"),
        ("Racha", f"{resumen['racha_dias']} d"),
        ("Prom. diario", f"{resumen['promedio_diario']:.1f} h"),
        ("Prom. semanal", f"{resumen['promedio_semanal']:.1f} h"),
    ]
    ancho = 190 / len(kpis)
    pdf.set_font("Helvetica", "", 8)
    for nombre, _ in kpis:
        pdf.cell(ancho, 5, _txt(nombre), align="C")
    pdf.ln()
    pdf.set_font("Helvetica", "B", 12)
    for _, valor in kpis:
        pdf.cell(ancho, 7, _txt(valor), align="C")
    pdf.ln(9)

    def seccion(titulo: str, imagen: BytesIO | None, nota: str | None = None) -> None:
        # Título + nota + imagen van JUNTOS: si no caben, página nueva antes del título.
        # Sin esto el salto automático de fpdf2 deja el título huérfano al pie.
        if imagen is not None:
            ancho_px, alto_px = Image.open(imagen).size
            imagen.seek(0)
            if pdf.get_y() + 190 * alto_px / ancho_px + 16 > pdf.page_break_trigger:
                pdf.add_page()
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, _txt(titulo), new_x="LMARGIN", new_y="NEXT")
        if nota:
            pdf.set_font("Helvetica", "", 8)
            pdf.multi_cell(0, 4, _txt(nota), new_x="LMARGIN", new_y="NEXT")
        if imagen is None:
            pdf.set_font("Helvetica", "I", 9)
            pdf.cell(0, 6, _txt("Sin datos suficientes."), new_x="LMARGIN", new_y="NEXT")
        else:
            pdf.image(imagen, w=190)
        pdf.ln(3)

    nota_tendencia = (
        f"Regresión lineal sobre {tendencia['semanas']} semanas: {tendencia['pendiente']:+.2f} h/semana "
        f"(R² {tendencia['r2']:.2f}). Proyección próxima semana: {tendencia['proyeccion']:.1f} h."
        if tendencia else "Se necesitan al menos 4 semanas para estimar una tendencia."
    )
    seccion("Horas por semana y tendencia", grafico_semanal(df, tendencia), nota_tendencia)
    seccion("Horas por proyecto", grafico_proyectos(df))
    seccion("Actividad por día de la semana", mapa_calor(df))

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, _txt("Días atípicos (IsolationForest)"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    if not atipicos:
        pdf.cell(0, 6, _txt("Ninguno (o menos de 10 días con registros)."), new_x="LMARGIN", new_y="NEXT")
    else:
        columnas = [("Fecha", 30), ("Horas", 25), ("Registros", 25), ("Puntaje", 25), ("Motivo", 85)]
        pdf.set_fill_color(230, 238, 250)
        for titulo, w in columnas:
            pdf.cell(w, 7, _txt(titulo), border=1, fill=True)
        pdf.ln()
        for a in atipicos:
            fila = [a["fecha"], f"{a['horas']:.2f}", a["registros"], f"{a['puntaje']:.3f}", a["motivo"]]
            for valor, (_, w) in zip(fila, columnas, strict=True):
                pdf.cell(w, 6, _txt(valor), border=1)
            pdf.ln()
    return bytes(pdf.output())
