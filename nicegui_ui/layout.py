"""
layout.py — Shell compartido de la UI: header, drawer, selector de tema y helpers.

El sistema visual (paleta, temas, defaults globales, CSS) vive en `tema.py`; aquí solo
se compone la página. Los helpers son deliberadamente cortos porque el aspecto de
tarjetas, tablas y campos ya lo fijan los `default_props`/`default_classes` globales
que `tema.aplicar_defaults()` instala al arrancar.

Responsividad: la deciden las clases Tailwind de las rejillas de abajo
(`REJILLA_*`), no anchos fijos en las vistas. Las vistas solo eligen qué rejilla usan.

Cada vista envuelve su contenido en `with shell("Título"):`.
"""

from contextlib import contextmanager

from nicegui import ui

from nicegui_ui import tema as t
from nicegui_ui.plotly_tema import config as config_plotly

# (ruta, icono Material, etiqueta) — mismas URLs que tenía la UI Streamlit.
PAGINAS = [
    ("/", "home", "Inicio"),
    ("/calendario", "calendar_month", "Calendario"),
    ("/liveops", "groups", "LiveOps Equipo"),
    ("/tareas", "task_alt", "Registro de Tareas"),
    ("/notas", "description", "Notas"),
    ("/tv", "tv", "TV Chile"),
    ("/apagado", "power_settings_new", "Apagado"),
]

# Rejillas responsivas reutilizables. Las métricas se reparten según CUÁNTAS son, para
# que las filas queden completas: con `auto-fit` las 6 de Tareas quedaban 5 + 1 a 1280 px.
# Los gráficos van a 1 columna en móvil, 2 desde tablet y 3 en pantallas anchas.
COLUMNAS_METRICAS = {
    1: "grid-cols-1",
    2: "grid-cols-2",
    3: "grid-cols-2 sm:grid-cols-3",
    4: "grid-cols-2 lg:grid-cols-4",
    5: "grid-cols-2 sm:grid-cols-3 lg:grid-cols-5",
    6: "grid-cols-2 sm:grid-cols-3 xl:grid-cols-6",
}
REJILLA_GRAFICOS = "w-full gap-4 grid-cols-1 md:grid-cols-2 2xl:grid-cols-3"
REJILLA_DOS = "w-full gap-6 grid-cols-1 md:grid-cols-2 items-start"


@contextmanager
def shell(titulo: str):
    """Layout común: tema de la página + drawer de navegación + header."""
    t.aplicar_a_pagina(titulo)

    # `aid-drawer`/`aid-header` (en vez de `bg-black`) es lo que tiñe el cromo con el
    # acento del tema: el degradado vive en el CSS global, que lee `--aid-acento`.
    # `value=None` = comportamiento responsivo de Quasar (`show-if-above`): abierto en
    # escritorio y CERRADO por debajo de 1024 px. Con `value=True` arrancaba abierto como
    # overlay en móvil y tablet, tapando la página en cada navegación.
    with ui.left_drawer(value=None, bordered=True).classes("aid-drawer p-3") as drawer:
        with ui.row().classes("items-center gap-2 no-wrap mb-1"):
            ui.image(t.MARCA).classes("aid-marca w-9 h-9")
            ui.label("All in Django").classes("text-lg font-bold")
        ui.label("Cliente NiceGUI de la API REST").classes("text-xs text-gray-400 mb-3")
        with ui.column().classes("w-full gap-1"):
            for ruta, icono, nombre in PAGINAS:
                activo = nombre == titulo
                ui.button(nombre, icon=icono, on_click=lambda r=ruta: ui.navigate.to(r)) \
                    .props("flat align=left color=white") \
                    .classes("w-full justify-start rounded-lg transition-colors"
                             + (" aid-nav-activo" if activo else ""))

    with ui.header().classes("aid-header items-center px-2 sm:px-3 no-wrap"):
        ui.button(icon="menu", on_click=drawer.toggle).props("flat dense color=white aria-label=Menu")
        ui.label(titulo).classes("text-base sm:text-lg font-medium truncate min-w-0")
        ui.space()
        selector_tema(titulo)

    # Ancho útil hasta 1600 px (antes `max-w-6xl` = 1152): en un monitor ancho el
    # dashboard tiene sitio para tres columnas de gráficos. Padding que crece con la
    # pantalla: 12 px en móvil, 24 px en escritorio.
    with ui.column().classes("w-full max-w-[1600px] mx-auto p-3 sm:p-4 lg:p-6 gap-4 min-w-0"):
        yield


# ─── Selector de tema (esquina superior derecha) ─────────────────────────────
def _elegir(clave: str) -> None:
    """Guarda la elección y recarga.

    Se probó el repintado en caliente (reescribir las custom properties): cubre fondo,
    aura, cromo y tablas, pero NO los botones `bg-primary`, a los que Quasar les resuelve
    el color al construirlos —ni con `!important` y más especificidad se recuperan—. Un
    botón con el color del tema anterior parece un fallo, así que se recarga: cambiar de
    tema es una acción deliberada y el render del servidor deja la página coherente.
    """
    t.fijar_tema(clave)
    ui.navigate.reload()


def selector_tema(titulo: str) -> None:
    """Aurora austral + los 16 personajes, más "Auto" (el personaje propio de cada página)."""
    activo = t.tema_activo(titulo)
    en_auto = t.tema_elegido() not in t.TEMAS
    with ui.button().props("flat dense color=white aria-label='Cambiar tema'").classes("px-2 shrink-0"):
        _miniatura(activo, "w-8 h-8")
        ui.icon("expand_more").classes("text-xs")
        ui.tooltip("Cambiar tema")
        with ui.menu().props("auto-close").classes("aid-tema-menu"):
            ui.item(("✓ " if en_auto else "") + "Auto (personaje por pagina)",
                    on_click=lambda: _elegir(t.TEMA_AUTO)) \
                .classes("text-xs" + (" text-primary" if en_auto else ""))
            ui.separator()
            with ui.grid(columns=4).classes("p-2 gap-1"):  # 4 × 80 px: cabe en 360 px
                for clave, tema in t.TEMAS.items():
                    # Se marca el tema EFECTIVO (en Auto, el de la página): el menú
                    # muestra qué se está viendo, no solo qué se eligió a mano.
                    _opcion(clave, tema, marcado=tema is activo)


def _miniatura(tema: t.Tema, tamano: str) -> None:
    """Miniatura de un tema: la figura del personaje o, en aurora, un trozo de cielo."""
    if tema.archivo:
        ui.image(f"{t.FONDOS_URL}/mini/{tema.archivo}").classes(f"aid-marca {tamano}")
    else:
        ui.element("span").classes(f"aid-muestra-aurora block {tamano}")


def _opcion(clave: str, tema: t.Tema, marcado: bool) -> None:
    clases = "aid-tema-opcion items-center gap-0.5 w-20 px-1 pt-1.5 pb-1 rounded-lg"
    # El click va en la COLUMNA, no en la imagen ni en la etiqueta: .mark() da a los tests
    # (y a cualquier automatización) un asidero sobre el elemento que de verdad escucha.
    with ui.column().classes(clases + (" aid-tema-elegido" if marcado else "")) \
            .mark(f"tema-{clave}") \
            .on("click", lambda: _elegir(clave)):
        _miniatura(tema, "w-12 h-14")
        ui.label(tema.etiqueta).classes("text-[10px] leading-tight text-center truncate w-full")
        ui.element("span").classes("aid-tema-punto").style(f"background: {tema.acento}")


def banda_tripulacion() -> None:
    """Banda de la portada con la tripulación al completo, a todo color.

    Va dentro de una `ui.card` para que herede el velo y el borde teñidos con el acento:
    la banda queda como una cubierta con la tripulación formada, no como doce PNG
    sueltos sobre el fondo. El rebote lo pone el default global de `ui.image`.
    """
    # `flex-nowrap` + scroll: la tripulación forma en UNA cubierta. Al envolver en
    # varias filas quedaba un rezagado suelto debajo, que leía como error de layout.
    # `justify-start` en móvil: con `center` y desborde, el primero quedaba cortado e
    # inalcanzable por scroll (el desborde centrado reparte la mitad a la izquierda).
    banda = "aid-banda w-full flex-nowrap justify-start lg:justify-center items-end gap-2 overflow-x-auto"
    with ui.card().classes("w-full p-3"), ui.row().classes(banda):
        for archivo in t.TRIPULACION:
            # Miniaturas: la banda pinta a 100 px, no hace falta el PNG completo.
            ui.image(f"{t.FONDOS_URL}/mini/{archivo}")


# ─── Helpers de contenido ────────────────────────────────────────────────────
def fila_metricas(cuantas: int):
    """Contenedor de `metric_card`: `with fila_metricas(3): metric_card(...) ...`."""
    return ui.grid().classes("w-full gap-3 " + COLUMNAS_METRICAS.get(cuantas, COLUMNAS_METRICAS[6]))


def rejilla_graficos():
    """Contenedor de `grafico`: 1 columna en móvil, 2 en tablet, 3 en pantallas anchas."""
    return ui.grid().classes(REJILLA_GRAFICOS)


def rejilla_dos():
    """Dos bloques lado a lado desde tablet; apilados en móvil (sustituye a `no-wrap`)."""
    return ui.grid().classes(REJILLA_DOS)


def metric_card(etiqueta: str, valor, extra: str | None = None) -> None:
    """Equivalente compacto de st.metric. El fondo y el borde vienen del default de
    `ui.card`, así que aquí solo va la composición."""
    with ui.card().tight().classes("px-4 py-3 items-start gap-0.5 w-full min-w-0"):
        # `aid-cifra` = el acento del tema como tinta (en aurora, un degradado), así la
        # cifra —lo que se mira— lleva el color de la página. No `text-primary`: es una
        # utilidad `!important` de Quasar y el degradado no podría reemplazarla.
        ui.label(str(valor)).classes("aid-cifra text-2xl font-bold leading-tight")
        ui.label(etiqueta).classes("text-xs text-gray-300")
        if extra:
            ui.label(extra).classes("text-xs text-green-400")


def _banner(icono: str, mensaje: str, color: str) -> None:
    with ui.row().classes(f"items-center no-wrap gap-2 rounded-lg p-3 w-full bg-{color}-900/30"):
        ui.icon(icono).classes(f"text-{color}-400 shrink-0")
        ui.label(mensaje).classes("min-w-0")


def aviso(mensaje: str) -> None:
    """Estado vacío / informativo (equivalente a st.info)."""
    _banner("info", mensaje, "blue")


def banner_error(mensaje: str) -> None:
    """Error persistente en página (no de acción: para eso está `notificar_error`)."""
    _banner("error", mensaje, "red")


def notificar_ok(mensaje: str) -> None:
    ui.notify(mensaje, type="positive", position="top")


def notificar_error(mensaje: str) -> None:
    ui.notify(mensaje, type="negative", position="top")


def tabla(filas: list[dict], columnas_ocultas: set[str] | None = None, alto: int = 340):
    """Tabla estilo st.dataframe: compacta, cabecera fija y scroll interno.

    Los props (`dense flat virtual-scroll`) y las clases las pone el default global de
    `ui.table`; aquí solo se derivan las columnas y se acota la altura. En móvil la
    tabla hace scroll HORIZONTAL dentro de sí misma (`q-table__middle`), nunca la página.
    """
    if not filas:
        return None
    ocultas = columnas_ocultas or set()
    claves = [k for k in filas[0] if k not in ocultas]
    columnas = [{"name": k, "label": k, "field": k, "sortable": True, "align": "left"}
                for k in claves]
    # pagination=0 → sin paginar; el scroll interno lo aporta virtual-scroll.
    return ui.table(columns=columnas, rows=filas, row_key=claves[0], pagination=0) \
             .style(f"max-height: {alto}px")


def grafico(fig, titulo: str | None = None, alto: str = "m", nombre: str = "grafico"):
    """Figura Plotly en una tarjeta con cabecera (título + pantalla completa).

    - `alto`: `s`/`m`/`l`/`xl` → clase `aid-alto-*`, una altura que depende del ancho
      (las figuras no fijan `height`; Plotly ocupa la del contenedor).
    - El botón de pantalla completa va en la CABECERA, no flotando sobre el gráfico:
      antes (absolute top-left) se superponía con el título y con la barra de Plotly.
      Se resuelve en el navegador (`js_handler`), sin ida y vuelta al servidor.
    - El reajuste de ancho al cambiar el contenedor (drawer, rejilla, pantalla
      completa) lo hace el ResizeObserver del componente `ui.plotly` de NiceGUI.
    """
    d = fig.to_plotly_json()
    d["config"] = config_plotly(nombre)
    with ui.card().classes("aid-graf w-full p-2 sm:p-3 gap-1") as tarjeta:
        with ui.row().classes("w-full items-center no-wrap gap-2 min-h-[2rem]"):
            if titulo:
                ui.label(titulo).classes("font-medium leading-tight grow min-w-0")
            else:
                ui.space()
            ui.button(icon="fullscreen") \
                .props("flat round dense color=white aria-label='Pantalla completa'") \
                .classes("aid-fsbtn shrink-0") \
                .on("click", js_handler=f"() => aidPantallaCompleta(getHtmlElement({tarjeta.id}))") \
                .tooltip("Pantalla completa")
        p = ui.plotly(d).classes(f"aid-lienzo aid-alto-{alto}")
    return p


def sin_datos(titulo: str, mensaje: str = "Sin datos suficientes.") -> None:
    """Tarjeta vacía con la misma cabecera que `grafico`, para no descuadrar la rejilla."""
    with ui.card().classes("aid-graf w-full p-2 sm:p-3 gap-1"):
        ui.label(titulo).classes("font-medium leading-tight")
        ui.label(mensaje).classes("text-xs text-gray-400")
