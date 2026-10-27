"""
plotly_tema.py — Plantilla Plotly propia de la UI y configuración común de los gráficos.

Módulo PURO (solo plotly): lo importan `charts.py` y `gantt.py`, que se prueban sin
runtime de UI, y `layout.grafico`, que dibuja. Así hay UN solo sitio que decide cómo se
ve un gráfico, y los Gantt —que antes no usaban ninguna plantilla y dibujaban ejes y
título en el azul marino por defecto de Plotly (#2a3f5f) sobre negro— heredan lo mismo
que el resto.

Paleta: la de referencia de la skill `dataviz`, en sus pasos para fondo OSCURO,
validada con `scripts/validate_palette.js --mode dark --surface #0c1222` (la superficie
de las tarjetas del tema Aurora): banda de luminosidad, croma, separación CVD de pares
adyacentes (peor ΔE 8,4), suelo de visión normal (19,3) y contraste ≥ 3:1. Todo en
verde. El ORDEN de los slots es parte de la validación: no se reordena sin re-validar.
"""

from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio

# ─── Tinta y superficies ─────────────────────────────────────────────────────
TINTA = "#E6EAF5"          # texto principal (títulos, valores)
TINTA_2 = "#B4BCD0"        # secundaria (ejes, leyenda)          9,6:1 sobre #0c1222
TINTA_SUAVE = "#8A93A8"    # ticks                                5,6:1 sobre #0c1222
REJILLA = "rgba(148, 163, 184, 0.12)"   # hairline: un tono sobre la superficie
EJE = "rgba(148, 163, 184, 0.28)"
SUPERFICIE_TOOLTIP = "#0F1630"

# ─── Paleta categórica (orden fijo, nunca ciclado) ───────────────────────────
PALETA = ["#3987e5", "#d95926", "#199e70", "#c98500",
          "#d55181", "#008300", "#9085e9", "#e66767"]
# Máximo de categorías con color propio: la novena NO es un tono generado, se pliega
# en "Otros" (regla de la skill dataviz).
MAX_CATEGORIAS = len(PALETA) - 1
COLOR_OTROS = "#5B6478"

# Rampa secuencial de UN solo tono (azul), de "casi nada" (pegado a la superficie) a
# "mucho" (claro): en fondo oscuro la magnitud sube hacia la luz.
SECUENCIAL = [[0.0, "#16203A"], [0.25, "#184f95"], [0.6, "#2a78d6"], [1.0, "#9ec5f4"]]

FUENTE = 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif'

PLANTILLA = "aid"


def _registrar() -> None:
    """Registra la plantilla `aid` sobre `plotly_dark` (se hereda lo que no se toca)."""
    base = go.layout.Template(pio.templates["plotly_dark"])
    base.layout.update(
        font=dict(family=FUENTE, color=TINTA_2, size=12),
        title=dict(font=dict(color=TINTA, size=14)),
        colorway=PALETA,
        # Lienzo transparente: la tarjeta (velo + blur) es la superficie.
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        # Márgenes mínimos + `automargin` en los ejes: Plotly reserva lo que necesitan
        # los ticks en vez de un margen fijo que sobra en escritorio y falta en móvil.
        margin=dict(l=8, r=8, t=8, b=8, pad=2),
        # Leyenda HORIZONTAL sobre el área de dibujo: la vertical a la derecha se comía
        # un tercio del ancho en móvil. Arriba (y no abajo) porque ahí Plotly le reserva
        # margen solo y no se pisa con los ticks del eje X a ningún ancho.
        legend=dict(orientation="h", x=0, xanchor="left", y=1.0, yanchor="bottom",
                    bgcolor="rgba(0,0,0,0)", font=dict(color=TINTA_2, size=11),
                    title=dict(text="")),
        hoverlabel=dict(bgcolor=SUPERFICIE_TOOLTIP, bordercolor=EJE,
                        font=dict(family=FUENTE, color=TINTA, size=12)),
        # Sin arrastre por defecto: en un móvil el dedo que arrastra sobre el gráfico
        # quiere hacer scroll de la página, no un zoom de caja. El zoom sigue a mano
        # desde la barra de herramientas (escritorio y pantalla completa).
        dragmode=False,
        bargap=0.28,
        barcornerradius=4,
        uniformtext=dict(minsize=9, mode="hide"),
    )
    for eje in ("xaxis", "yaxis"):
        base.layout[eje].update(
            gridcolor=REJILLA, linecolor=EJE, zerolinecolor=EJE, automargin=True,
            tickfont=dict(color=TINTA_SUAVE, size=11), title=dict(font=dict(color=TINTA_2, size=12)),
        )
    pio.templates[PLANTILLA] = base


_registrar()

# ─── Configuración del cliente (plotly.js) ───────────────────────────────────
# Botones que sobran en un panel personal: los de selección, autoscale y las variantes
# de hover. Con 11 iconos la barra se partía en 2-3 filas a 360 px y ocupaba más que el
# gráfico. Quedan: descargar PNG, zoom, pan y reset.
_SIN_BOTONES = ["select2d", "lasso2d", "autoScale2d", "zoomIn2d", "zoomOut2d",
                "toggleSpikelines", "hoverClosestCartesian", "hoverCompareCartesian",
                "toggleHover", "resetViews"]


def config(nombre: str = "grafico") -> dict:
    """`config` de plotly.js para `ui.plotly`.

    `displayModeBar: "hover"` la muestra solo al pasar el ratón; en táctil y en
    pantallas chicas además la oculta el CSS de `tema.py` (salvo en pantalla completa).
    """
    return {
        "displaylogo": False,
        "responsive": True,
        "displayModeBar": "hover",
        "modeBarButtonsToRemove": _SIN_BOTONES,
        "scrollZoom": False,
        "doubleClick": "reset",
        "toImageButtonOptions": {"format": "png", "scale": 2, "filename": nombre},
    }


def truncar(texto: str, largo: int = 18) -> str:
    """Etiqueta de eje acotada: el nombre completo viaja en el tooltip."""
    texto = str(texto)
    return texto if len(texto) <= largo else texto[: largo - 1].rstrip() + "…"
