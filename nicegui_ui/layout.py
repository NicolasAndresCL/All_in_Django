"""
layout.py — Shell compartido de la UI NiceGUI: tema, header + drawer y helpers.

Tema base: "Dark High Contrast" de VS Code (fondo negro puro, bordes cian de
contraste, foco naranja). Se aplica con `ui.colors` (marcas Quasar) + CSS inyectado.

Sobre esa base va la **identidad por página** (ver `IDENTIDAD`): cada vista tiene un
personaje de fondo y un color de acento propio, de forma que navegar por la app se
sienta como recorrer la tripulación. Reglas de diseño que sostienen lo "elegante":

- El personaje es una **marca de agua**, no una foto de fondo: opacidad baja, anclado
  abajo a la derecha y disuelto con `mask-image` para que no tenga bordes duros.
- El contraste manda: el texto sigue siendo blanco sobre negro y las superficies con
  datos (tarjetas, tablas) llevan un velo casi opaco con desenfoque, así que la
  legibilidad no depende de qué haya detrás.
- El acento NO reemplaza el borde cian estructural (esa es la identidad del tema HC):
  colorea el riel del header, el elemento activo del menú y el halo de la página.

Los acentos salen de las propias imágenes (`scripts/preparar_fondos.py` calcula el
tono dominante ponderado por saturación); ver la nota de Robin más abajo.

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
    ("/apagado", "power_settings_new", "Apagado"),
]

# Prefijo con el que `main.py` publica nicegui_ui/static/fondos/.
FONDOS_URL = "/fondos"

# Emblema de la app en el drawer: la bandera de los Mugiwara.
MARCA = f"{FONDOS_URL}/mugiwara.png"

# Página → (imagen de fondo, acento). El reparto es semántico, no decorativo:
#   Calendario  → Nami, la navegante que traza el rumbo.
#   LiveOps     → Jinbe, el timonel que coordina a la tripulación.
#   Tareas      → Zoro, disciplina y entrenamiento.
#   Notas       → Robin, la arqueóloga que lee y transcribe los poneglifos.
#   TV Chile    → Brook, el músico y showman.
#   Apagado     → el sombrero solo, colgado: fuera de servicio.
# El acento es el que calcula `preparar_fondos.py`, salvo Robin: su tono dominante
# medido es carmesí (#FF3848, de zapatos y labios) y chocaba con el rojo de Jinbe,
# así que se usa el rosa de su vestido —su color reconocible— separando ambas páginas.
IDENTIDAD = {
    "Inicio": ("onePiece.png", "#38CDFF"),
    "Calendario": ("nami.png", "#FF6938"),
    "LiveOps Equipo": ("jinbe.png", "#FF4838"),
    "Registro de Tareas": ("zoro.png", "#38FF8A"),
    "Notas": ("robin.png", "#FF3898"),
    "TV Chile": ("brook.png", "#388AFF"),
    "Apagado": ("sombrero.png", "#FFCD38"),
}
IDENTIDAD_POR_DEFECTO = ("mugiwara.png", "#2AAAFF")

# Tripulación completa: banda decorativa de la portada. Solo personajes y el barco:
# los emblemas (mugiwara, sombrero, aot) a 62 px de ancho leen como una mancha, no
# como una figura, así que se quedan fuera de la banda.
TRIPULACION = ["Luffy.png", "zoro.png", "nami.png", "usopp.png", "sanji.png",
               "chopper.png", "robin.png", "franky.png", "brook.png", "jinbe.png",
               "mikasa.png", "sunny.png"]

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
body, .q-drawer, .q-header {{ background: {_BG} !important; color: {_TEXT} !important; }}
/* El contenedor de la página va TRANSPARENTE: si pinta negro opaco tapa la capa de
   fondo (que vive en body::before/::after) y la marca de agua no se ve. */
.q-page, .nicegui-content {{ background: transparent !important; color: {_TEXT} !important; }}
.q-header {{ border-bottom: 1px solid var(--aid-border) !important; }}
.q-drawer {{ border-right: 1px solid var(--aid-border) !important; }}
/* Las superficies con datos van sobre un velo casi opaco: la marca de agua se
   insinúa detrás pero NUNCA compite con el contenido. */
.q-card {{
    background: rgba(6, 6, 6, 0.82) !important;
    border: 1px solid var(--aid-border) !important;
    backdrop-filter: blur(6px);
}}
.text-gray-500, .text-gray-400 {{ color: {_MUTED} !important; }}
a, .q-link, .text-primary {{ color: #3794FF !important; }}
/* Inputs/select con borde de contraste y foco naranja. Llevan velo propio: un campo
   transparente deja ver la marca de agua DENTRO del área de escritura. */
.q-field--outlined .q-field__control {{ background: rgba(6, 6, 6, 0.78) !important; }}
.q-field--outlined .q-field__control:before {{ border-color: var(--aid-border) !important; }}
*:focus-visible {{ outline: 2px solid var(--aid-focus) !important; outline-offset: 1px; }}
.q-btn {{ border: 1px solid transparent; }}
.q-btn:focus-visible {{ outline: 2px solid var(--aid-focus) !important; }}
/* Tablas estilo Streamlit: compactas, cabecera fija, scroll interno */
.aid-table {{
    background: rgba(6, 6, 6, 0.86) !important;
    border: 1px solid var(--aid-border) !important;
    backdrop-filter: blur(6px);
}}
.aid-table thead tr th {{
    position: sticky; top: 0; z-index: 2;
    background: #050505 !important; color: var(--aid-acento) !important; font-weight: 600;
    border-bottom: 1px solid var(--aid-border) !important;
}}
.aid-table td, .aid-table th {{ border-color: #2a2a2a !important; }}
.aid-table .q-table__bottom {{ border-top: 1px solid var(--aid-border) !important; }}
/* Botón de pantalla completa sobre cada gráfico */
.aid-graf {{ position: relative; }}
.aid-fsbtn {{ position: absolute; top: 4px; left: 4px; z-index: 5; }}

/* ── Capa de fondo ────────────────────────────────────────────────────────
   Dos pseudo-elementos fijos y NO interactivos detrás de todo:
   ::before = marca de agua del personaje, ::after = halo del color de página. */
body::before, body::after {{
    content: ""; position: fixed; inset: 0;
    pointer-events: none; z-index: 0;
}}
body::before {{
    background-image: var(--aid-fondo);
    background-repeat: no-repeat;
    /* Inset por la derecha: si sobresale, el viewport la recorta con un canto recto.
       Por abajo sí sangra, que ahí el corte se confunde con el borde de la ventana. */
    background-position: right 1.5vw bottom -5vh;
    background-size: auto 66vh;
    opacity: 0.10;
    /* Viñeta: la figura se disuelve en todas direcciones desde su esquina, así no
       queda "pegada" con bordes duros ni compite con el texto del centro. */
    -webkit-mask-image: radial-gradient(ellipse 78% 84% at 88% 96%,
                                        #000 18%, rgba(0,0,0,.55) 52%, transparent 78%);
    mask-image: radial-gradient(ellipse 78% 84% at 88% 96%,
                                #000 18%, rgba(0,0,0,.55) 52%, transparent 78%);
}}
body::after {{
    background:
        radial-gradient(1100px 620px at 12% -8%,
                        color-mix(in srgb, var(--aid-acento) 16%, transparent), transparent 70%),
        radial-gradient(900px 700px at 108% 106%,
                        color-mix(in srgb, var(--aid-acento) 11%, transparent), transparent 68%);
}}
/* El contenido va por encima de la capa de fondo. Header y drawer NO se tocan: Quasar
   los posiciona `fixed` con su propio z-index, y forzarles `position: relative` los
   devuelve al flujo (el drawer deja de ser lateral y empuja la página hacia abajo). */
.nicegui-content, .q-page {{ position: relative; z-index: 1; }}

/* Riel de acento del header + elemento activo del menú. */
.q-header {{ box-shadow: inset 0 3px 0 0 var(--aid-acento); }}
.aid-nav-activo {{
    color: var(--aid-acento) !important;
    box-shadow: inset 3px 0 0 0 var(--aid-acento);
    background: color-mix(in srgb, var(--aid-acento) 12%, transparent) !important;
}}
.aid-marca {{ filter: drop-shadow(0 0 10px color-mix(in srgb, var(--aid-acento) 55%, transparent)); }}

/* Banda de tripulación de la portada. */
.aid-banda {{
    display: flex; align-items: flex-end; justify-content: center;
    gap: 1.4rem; width: 100%; height: 92px; overflow: hidden; opacity: 0.55;
    -webkit-mask-image: linear-gradient(to right, transparent, #000 12%, #000 88%, transparent);
    mask-image: linear-gradient(to right, transparent, #000 12%, #000 88%, transparent);
}}
/* `ui.image` envuelve el <img> en un div .q-img que, sin tamaño explícito, se estira
   a todo el ancho disponible. El tamaño se fija en el WRAPPER, no en el <img>. */
.aid-banda .q-img {{
    flex: 0 0 auto; height: 84px; width: 62px; min-height: 0;
    filter: grayscale(1) brightness(1.7); opacity: 0.62;
    transition: filter .25s ease, opacity .25s ease, transform .25s ease;
}}
.aid-banda .q-img > img {{ object-fit: contain; object-position: bottom; }}
.aid-banda .q-img:hover {{ filter: none; opacity: 1; transform: translateY(-6px); }}
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


def identidad(titulo: str) -> tuple[str, str]:
    """(URL de la imagen de fondo, color de acento) de la página `titulo`."""
    imagen, acento = IDENTIDAD.get(titulo, IDENTIDAD_POR_DEFECTO)
    return f"{FONDOS_URL}/{imagen}", acento


def _aplicar_tema(titulo: str) -> None:
    fondo, acento = identidad(titulo)
    ui.dark_mode(value=True)
    # El acento de la página pasa a ser el `primary` de Quasar: botones y controles
    # heredan el color del personaje sin CSS extra.
    ui.colors(primary=acento, secondary=_BORDER, accent=_FOCUS,
              positive="#23D18B", negative="#F14C4C", warning=_FOCUS,
              dark=_BG, dark_page=_BG)
    ui.add_head_html(_CSS)
    ui.add_head_html(
        f"<style>:root {{ --aid-acento: {acento}; --aid-fondo: url('{fondo}'); }}</style>"
    )
    ui.add_head_html(_FS_HEAD)


@contextmanager
def shell(titulo: str):
    """Layout común: tema HC + identidad de la página + header y drawer."""
    _aplicar_tema(titulo)

    with ui.left_drawer(value=True, bordered=True) as drawer:
        with ui.row().classes("items-center gap-2 q-mb-xs no-wrap"):
            ui.image(MARCA).classes("aid-marca w-9 h-9").props("no-spinner fit=contain")
            ui.label("All in Django").classes("text-lg font-bold")
        ui.label("Cliente NiceGUI de la API REST").classes("text-xs text-gray-500 q-mb-md")
        for ruta, icono, nombre in PAGINAS:
            activo = nombre == titulo
            ui.button(nombre, icon=icono, on_click=lambda r=ruta: ui.navigate.to(r)) \
                .props("flat align=left color=white") \
                .classes("w-full justify-start" + (" aid-nav-activo" if activo else ""))

    with ui.header().classes("items-center"):
        ui.button(icon="menu", on_click=drawer.toggle).props("flat color=white dense")
        ui.label(titulo).classes("text-lg font-medium")

    with ui.column().classes("w-full max-w-6xl mx-auto p-4 gap-4"):
        yield


def banda_tripulacion() -> None:
    """Banda decorativa con la tripulación al completo (portada). En gris, se colorea
    al pasar el ratón: expresiva sin robarle atención a los datos."""
    with ui.row().classes("aid-banda"):
        for archivo in TRIPULACION:
            # Miniaturas: la banda pinta a 84 px, no hace falta bajar el PNG completo.
            ui.image(f"{FONDOS_URL}/mini/{archivo}").props("no-spinner fit=contain")


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
    # Lienzo transparente: el gráfico se apoya en el fondo de la página en vez de
    # recortar un rectángulo gris de `plotly_dark` encima de la marca de agua.
    d.setdefault("layout", {}).update(paper_bgcolor="rgba(0,0,0,0)",
                                      plot_bgcolor="rgba(0,0,0,0)")
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
