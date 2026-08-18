"""
layout.py — Shell compartido de la UI: header, drawer, selector de tema y helpers.

El sistema visual (paleta, temas, defaults globales, CSS) vive en `tema.py`; aquí solo
se compone la página. Los helpers son deliberadamente cortos porque el aspecto de
tarjetas, tablas y campos ya lo fijan los `default_props`/`default_classes` globales
que `tema.aplicar_defaults()` instala al arrancar.

Cada vista envuelve su contenido en `with shell("Título"):`.
"""

from contextlib import contextmanager

from nicegui import ui

from nicegui_ui import tema as t

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


@contextmanager
def shell(titulo: str):
    """Layout común: tema de la página + drawer de navegación + header."""
    t.aplicar_a_pagina(titulo)

    # `aid-drawer`/`aid-header` (en vez de `bg-black`) es lo que tiñe el cromo con el
    # acento del personaje: el degradado vive en el CSS global, que lee `--aid-acento`.
    with ui.left_drawer(value=True, bordered=True).classes("aid-drawer p-3") as drawer:
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

    with ui.header().classes("aid-header items-center px-3"):
        ui.button(icon="menu", on_click=drawer.toggle).props("flat dense color=white")
        ui.label(titulo).classes("text-lg font-medium")
        ui.space()
        selector_tema(titulo)

    with ui.column().classes("w-full max-w-6xl mx-auto p-4 gap-4"):
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
    """Los 16 personajes como temas, más "Auto" (el personaje propio de cada página)."""
    activo = t.tema_activo(titulo)
    en_auto = t.tema_elegido() not in t.TEMAS
    with ui.button().props("flat dense color=white").classes("px-2"):
        ui.image(f"{t.FONDOS_URL}/mini/{activo.archivo}").classes("aid-marca w-8 h-8")
        ui.icon("expand_more").classes("text-xs")
        ui.tooltip("Cambiar tema")
        with ui.menu().props("auto-close").classes("aid-tema-menu"):
            ui.item(("✓ " if en_auto else "") + "Auto (personaje por pagina)",
                    on_click=lambda: _elegir(t.TEMA_AUTO)) \
                .classes("text-xs" + (" text-primary" if en_auto else ""))
            ui.separator()
            with ui.grid(columns=4).classes("p-2 gap-1"):
                for clave, tema in t.TEMAS.items():
                    # Se marca el tema EFECTIVO (en Auto, el de la página): el menú
                    # muestra qué se está viendo, no solo qué se eligió a mano.
                    _opcion(clave, tema, marcado=tema is activo)


def _opcion(clave: str, tema: t.Tema, marcado: bool) -> None:
    clases = "aid-tema-opcion items-center gap-0.5 w-20 px-1 pt-1.5 pb-1 rounded-lg"
    with ui.column().classes(clases + (" aid-tema-elegido" if marcado else "")) \
            .on("click", lambda: _elegir(clave)):
        ui.image(f"{t.FONDOS_URL}/mini/{tema.archivo}").classes("w-12 h-14")
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
    banda = "aid-banda w-full flex-nowrap justify-center items-end gap-2 overflow-x-auto"
    with ui.card().classes("w-full p-3"), ui.row().classes(banda):
        for archivo in t.TRIPULACION:
            # Miniaturas: la banda pinta a 100 px, no hace falta el PNG completo.
            ui.image(f"{t.FONDOS_URL}/mini/{archivo}")


# ─── Helpers de contenido ────────────────────────────────────────────────────
def metric_card(etiqueta: str, valor, extra: str | None = None) -> None:
    """Equivalente compacto de st.metric. El fondo y el borde vienen del default de
    `ui.card`, así que aquí solo va la composición."""
    with ui.card().tight().classes("px-4 py-3 items-center min-w-[130px]"):
        # `text-primary` = el acento del personaje activo (lo fija `ui.colors`), así la
        # cifra —lo que se mira— lleva el color de la página.
        ui.label(str(valor)).classes("text-2xl font-bold text-primary")
        ui.label(etiqueta).classes("text-xs text-gray-400")
        if extra:
            ui.label(extra).classes("text-xs text-green-400")


def _banner(icono: str, mensaje: str, color: str) -> None:
    with ui.row().classes(f"items-center gap-2 rounded-lg p-3 w-full bg-{color}-900/30"):
        ui.icon(icono).classes(f"text-{color}-400")
        ui.label(mensaje)


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
    `ui.table`; aquí solo se derivan las columnas y se acota la altura.
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


def grafico(fig):
    """Figura Plotly con la barra de herramientas completa y botón de pantalla completa."""
    d = fig.to_plotly_json()
    d["config"] = {"displaylogo": False, "responsive": True, "displayModeBar": True}
    # Lienzo transparente: el gráfico se apoya en el fondo de la página en vez de
    # recortar un rectángulo gris encima de la marca de agua.
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
