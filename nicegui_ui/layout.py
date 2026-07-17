"""
layout.py — Shell compartido de la UI NiceGUI: tema, header + drawer y helpers.

Tema: "Dark High Contrast" de VS Code (fondo negro puro, bordes cian de contraste,
foco naranja). Se aplica con `ui.colors` (marcas Quasar) + CSS global inyectado.

Cada vista envuelve su contenido en `with shell("Título"):`.
"""

from contextlib import contextmanager

from nicegui import ui

# (ruta, icono Material, etiqueta) — mismas URLs que la UI Streamlit.
PAGINAS = [
    ("/", "home", "Inicio"),
    ("/calendario", "calendar_month", "Calendario"),
    ("/liveops", "groups", "LiveOps Equipo"),
    ("/tareas", "task_alt", "Registro de Tareas"),
    ("/notas", "description", "Notas"),
    ("/tv", "tv", "TV Chile"),
]

# Dashboard/Gantt: la plantilla plotly acompaña al tema oscuro de la UI.
PLOTLY_TEMPLATE = "plotly_dark"

# ─── Tema: VS Code Dark High Contrast ────────────────────────────────────────
_BG = "#000000"          # editor.background (negro puro)
_BORDER = "#6FC3DF"      # contrastBorder (cian)
_FOCUS = "#F38518"       # focusBorder (naranja)
_PRIMARY = "#2AAAFF"     # acento azul brillante
_TEXT = "#FFFFFF"
_MUTED = "#C5C5C5"

_CSS = f"""
<style>
:root {{ --aid-border: {_BORDER}; --aid-focus: {_FOCUS}; }}
body, .q-page, .nicegui-content, .q-drawer, .q-header {{
    background: {_BG} !important; color: {_TEXT} !important;
}}
.q-header {{ border-bottom: 1px solid var(--aid-border) !important; }}
.q-drawer {{ border-right: 1px solid var(--aid-border) !important; }}
.q-card {{ background: {_BG} !important; border: 1px solid var(--aid-border) !important; }}
.text-gray-500, .text-gray-400 {{ color: {_MUTED} !important; }}
a, .q-link, .text-primary {{ color: #3794FF !important; }}
/* Inputs/select con borde de contraste y foco naranja */
.q-field--outlined .q-field__control:before {{ border-color: var(--aid-border) !important; }}
*:focus-visible {{ outline: 2px solid var(--aid-focus) !important; outline-offset: 1px; }}
.q-btn {{ border: 1px solid transparent; }}
.q-btn:focus-visible {{ outline: 2px solid var(--aid-focus) !important; }}
/* Tablas estilo Streamlit: compactas, cabecera fija, scroll interno */
.aid-table {{ background: {_BG} !important; border: 1px solid var(--aid-border) !important; }}
.aid-table thead tr th {{
    position: sticky; top: 0; z-index: 2;
    background: {_BG} !important; color: {_BORDER} !important; font-weight: 600;
    border-bottom: 1px solid var(--aid-border) !important;
}}
.aid-table td, .aid-table th {{ border-color: #2a2a2a !important; }}
.aid-table .q-table__bottom {{ border-top: 1px solid var(--aid-border) !important; }}
/* Botón de pantalla completa sobre cada gráfico */
.aid-graf {{ position: relative; }}
.aid-fsbtn {{ position: absolute; top: 4px; left: 4px; z-index: 5; }}
</style>
"""

# Resize de los gráficos plotly al entrar/salir de pantalla completa (un solo listener).
_FS_HEAD = """
<script>
if (!window._aidFsInit) {
  window._aidFsInit = true;
  document.addEventListener('fullscreenchange', () => setTimeout(() => {
    document.querySelectorAll('.js-plotly-plot').forEach(p => {
      if (window.Plotly) window.Plotly.Plots.resize(p);
    });
  }, 120));
}
</script>
"""


def _aplicar_tema() -> None:
    ui.dark_mode(value=True)
    ui.colors(primary=_PRIMARY, secondary=_BORDER, accent=_FOCUS,
              positive="#23D18B", negative="#F14C4C", warning=_FOCUS,
              dark=_BG, dark_page=_BG)
    ui.add_head_html(_CSS)
    ui.add_head_html(_FS_HEAD)


@contextmanager
def shell(titulo: str):
    """Layout común: tema HC + header con título + drawer de navegación."""
    _aplicar_tema()

    with ui.left_drawer(value=True, bordered=True) as drawer:
        ui.label("🗂️ All in Django").classes("text-lg font-bold q-mb-md")
        ui.label("Cliente NiceGUI de la API REST").classes("text-xs text-gray-500 q-mb-md")
        for ruta, icono, nombre in PAGINAS:
            activo = nombre == titulo
            ui.button(nombre, icon=icono, on_click=lambda r=ruta: ui.navigate.to(r)) \
                .props(f"flat align=left {'color=primary' if activo else 'color=white'}") \
                .classes("w-full justify-start")

    with ui.header().classes("items-center"):
        ui.button(icon="menu", on_click=drawer.toggle).props("flat color=white dense")
        ui.label(titulo).classes("text-lg font-medium")

    with ui.column().classes("w-full max-w-6xl mx-auto p-4 gap-4"):
        yield


def metric_card(etiqueta: str, valor, extra: str | None = None) -> None:
    """Equivalente compacto de st.metric: tarjeta con valor grande + etiqueta."""
    with ui.card().tight().classes("px-4 py-3 items-center min-w-[130px]"):
        ui.label(str(valor)).classes("text-2xl font-bold")
        ui.label(etiqueta).classes("text-xs text-gray-500")
        if extra:
            ui.label(extra).classes("text-xs text-green-500")


def aviso(mensaje: str) -> None:
    """Estado vacío / informativo (equivalente a st.info)."""
    with ui.row().classes("items-center bg-blue-900/30 rounded p-3 w-full"):
        ui.icon("info").classes("text-blue-400")
        ui.label(mensaje)


def banner_error(mensaje: str) -> None:
    """Error persistente en página (equivalente a st.error de estado, no de acción)."""
    with ui.row().classes("items-center bg-red-900/30 rounded p-3 w-full"):
        ui.icon("error").classes("text-red-400")
        ui.label(mensaje)


def notificar_ok(mensaje: str) -> None:
    ui.notify(mensaje, type="positive", position="top")


def notificar_error(mensaje: str) -> None:
    ui.notify(mensaje, type="negative", position="top")


def tabla(filas: list[dict], columnas_ocultas: set[str] | None = None, alto: int = 340):
    """Tabla estilo st.dataframe: compacta, cabecera fija y scroll interno (no vuelca
    todas las filas a lo largo de la página). Ordenable por columna."""
    if not filas:
        return None
    ocultas = columnas_ocultas or set()
    claves = [k for k in filas[0].keys() if k not in ocultas]
    columns = [{"name": k, "label": k, "field": k, "sortable": True, "align": "left"}
               for k in claves]
    t = ui.table(columns=columns, rows=filas, row_key=claves[0],
                 pagination=0)  # 0 = sin paginar; el scroll interno lo aporta virtual-scroll
    t.props("dense flat virtual-scroll").classes("aid-table w-full")
    t.style(f"max-height: {alto}px")
    return t


def grafico(fig):
    """Dibuja una figura Plotly con la barra de herramientas COMPLETA (zoom/pan/box/
    lasso/descarga…) y un botón de pantalla completa (como el expandir de Streamlit)."""
    d = fig.to_plotly_json()
    d["config"] = {"displaylogo": False, "responsive": True, "displayModeBar": True}
    with ui.element("div").classes("aid-graf w-full"):
        p = ui.plotly(d).classes("w-full")
        ui.button(icon="fullscreen",
                  on_click=lambda: ui.run_javascript(
                      f"const e = getHtmlElement({p.id});"
                      f"if (document.fullscreenElement) document.exitFullscreen();"
                      f"else e.requestFullscreen();")) \
            .props("flat round dense color=white") \
            .classes("aid-fsbtn bg-black/50").tooltip("Pantalla completa")
    return p
