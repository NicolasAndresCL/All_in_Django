"""
Tests del sistema visual (`nicegui_ui.tema`).

Protegen invariantes que se rompen en silencio: un nombre de archivo mal escrito deja
la página sin fondo sin que falle nada, dos páginas con el mismo acento anulan el
propósito del diseño, y una opacidad fuera de rango o apaga la figura o rompe el
contraste con el texto.
"""

import inspect
import os
import re

import pytest
from nicegui import ui

from nicegui_ui import layout, tema

ESTATICOS = os.path.join(os.path.dirname(tema.__file__), "static", "fondos")

# Suelo y techo de opacidad, en sintonía con `scripts/preparar_fondos.py`. El suelo es
# lo que garantiza que la figura SE VEA (cara incluida); el techo, que siga habiendo
# margen de contraste. Ver OPACIDAD_MIN/MAX del pipeline.
OPACIDAD_MIN, OPACIDAD_MAX = 0.36, 0.80


def _ruta(archivo: str, mini: bool = False) -> str:
    return os.path.join(ESTATICOS, "mini", archivo) if mini else os.path.join(ESTATICOS, archivo)


# ─── catálogo de temas ───────────────────────────────────────────────────────
PERSONAJES = sorted((c, t) for c, t in tema.TEMAS.items() if t.archivo)


@pytest.mark.parametrize("clave, t", PERSONAJES)
def test_cada_tema_apunta_a_imagenes_existentes(clave, t):
    assert os.path.isfile(_ruta(t.archivo)), f"{clave}: falta {t.archivo}"
    assert os.path.isfile(_ruta(t.archivo, mini=True)), f"{clave}: falta su miniatura"


@pytest.mark.parametrize("clave, t", PERSONAJES)
def test_cada_tema_tiene_acento_hex_y_opacidad_util(clave, t):
    assert re.fullmatch(r"#[0-9A-F]{6}", t.acento), f"{clave}: acento {t.acento}"
    assert OPACIDAD_MIN <= t.opacidad <= OPACIDAD_MAX, f"{clave}: opacidad {t.opacidad}"
    assert t.etiqueta.strip(), f"{clave}: sin etiqueta para el selector"


def test_hay_un_tema_por_cada_imagen_disponible():
    """Si se añade un PNG al pipeline, debe aparecer en el selector: si no, queda
    procesado y pesando en la imagen Docker pero inalcanzable."""
    en_disco = {f for f in os.listdir(ESTATICOS) if f.endswith(".png")}
    en_temas = {t.archivo for t in tema.TEMAS.values() if t.archivo}
    assert en_disco == en_temas, f"sin tema: {en_disco - en_temas}"


# ─── identidad por página ────────────────────────────────────────────────────
@pytest.mark.parametrize("titulo", [nombre for _, _, nombre in layout.PAGINAS])
def test_cada_pagina_del_menu_tiene_identidad(titulo):
    assert titulo in tema.IDENTIDAD


@pytest.mark.parametrize("titulo, clave", sorted(tema.IDENTIDAD.items()))
def test_la_identidad_apunta_a_un_tema_real(titulo, clave):
    assert clave in tema.TEMAS


def test_el_tema_por_defecto_existe():
    assert tema.IDENTIDAD_POR_DEFECTO in tema.TEMAS


def test_los_acentos_son_distintos_entre_paginas():
    """El color es lo que distingue una sección de otra; repetirlo rompe el sistema."""
    acentos = [tema.TEMAS[c].acento for c in tema.IDENTIDAD.values()]
    assert len(set(acentos)) == len(acentos), f"acentos repetidos: {acentos}"


@pytest.mark.parametrize("archivo", sorted(tema.TRIPULACION))
def test_la_banda_usa_miniaturas_existentes(archivo):
    assert os.path.isfile(_ruta(archivo, mini=True)), f"falta la miniatura de {archivo}"


# ─── resolución del tema activo ──────────────────────────────────────────────
def test_en_auto_manda_el_personaje_de_la_pagina():
    assert tema.tema_activo("Notas", tema.TEMA_AUTO) is tema.TEMAS["robin"]


def test_una_pagina_desconocida_cae_al_tema_por_defecto():
    assert tema.tema_activo("Pagina Inventada", tema.TEMA_AUTO)         is tema.TEMAS[tema.IDENTIDAD_POR_DEFECTO]


def test_sin_contexto_de_usuario_el_tema_es_el_por_defecto():
    """`app.storage.user` exige contexto de petición. Fuera de él (tests, importación)
    no debe reventar: la respuesta es el tema por defecto, que desde la 2.2.0 es aurora."""
    assert tema.tema_elegido() == tema.TEMA_POR_DEFECTO == tema.TEMA_AURORA
    assert tema.tema_activo("Notas") is tema.TEMAS[tema.TEMA_AURORA]


def test_un_tema_elegido_a_mano_manda_sobre_la_pagina():
    assert tema.tema_activo("Notas", "brook") is tema.TEMAS["brook"]


# ─── variables CSS ───────────────────────────────────────────────────────────
def test_las_variables_css_cubren_todo_lo_que_define_el_tema():
    css = tema.variables(tema.TEMAS["brook"])
    assert "--aid-acento: #388AFF;" in css
    assert f"--aid-fondo: url('{tema.FONDOS_URL}/brook.png');" in css
    assert "--aid-opacidad: 0.78;" in css


# ─── capa visual: cubierta, cromo teñido y movimiento ────────────────────────
def test_el_fondo_dibuja_la_cubierta_de_madera():
    """La madera es procedural (gradientes), no un asset: si alguien la sustituye por
    una textura hay que enterarse, porque vuelve a pesar y a repetirse a la vista."""
    assert tema.CUBIERTA.count("repeating-linear-gradient") >= 2
    assert "background-attachment: fixed;" in tema.CUBIERTA


def test_la_cubierta_viaja_en_el_estilo_inline_de_body_y_sin_bg_black():
    """Dos trampas ya pagadas, comprobadas en el navegador:

    1. En la hoja global la cubierta no se dibuja (Quasar pinta `body.body--dark` con
       el shorthand `background`, que resetea `background-image`); tiene que ir inline.
    2. Con la clase `bg-black` puesta tampoco: esa utilidad es `background: #000
       !important` y gana incluso al inline. El negro lo pinta la propia `CUBIERTA`.
    """
    assert tema.CUBIERTA in tema.variables(tema.TEMAS["nami"])
    assert "background-image" not in tema._CSS.split("body::before", 1)[0]
    assert f"background-color: {tema.FONDO};" in tema.CUBIERTA
    clases = re.findall(r'classes\("([^"]*)"\)', inspect.getsource(tema.aplicar_a_pagina))
    assert clases and all("bg-black" not in c for c in clases), clases


@pytest.mark.parametrize("selector", [".aid-header", ".aid-drawer", ".aid-superficie"])
def test_el_cromo_y_las_tarjetas_se_tinen_con_el_acento(selector):
    """Sidebar, navbar y tarjetas deben leer `--aid-acento`: es lo que hace que cada
    personaje se reconozca en toda la interfaz, no solo en la marca de agua."""
    bloque = tema._CSS.split(selector, 1)[1].split("}", 1)[0]
    assert "--aid-acento" in bloque, f"{selector} no usa el acento del tema"


def test_las_clases_propias_que_usa_el_layout_estan_definidas_en_el_css():
    """Una clase `aid-*` mal escrita en `layout.py` no falla: simplemente no estiliza.
    Este test convierte ese silencio en un error."""
    # `(?<![-\w])` descarta las custom properties (`--aid-acento`): no son clases.
    usadas = set(re.findall(r"(?<![-\w])aid-[a-z-]+", inspect.getsource(layout)))
    faltan = {c for c in usadas if f".{c}" not in tema._CSS}
    assert not faltan, f"clases sin CSS: {sorted(faltan)}"


def test_toda_imagen_rebota_por_defecto():
    """El rebote se declara UNA vez (default global), no clase a clase en las vistas."""
    tema.aplicar_defaults()
    assert "aid-rebote" in ui.image._default_classes


def test_el_movimiento_respeta_prefers_reduced_motion():
    """Accesibilidad: quien pide menos movimiento se queda con el diseño quieto."""
    bloque = tema._CSS.split("prefers-reduced-motion", 1)[1][:200]
    assert "animation: none !important" in bloque
    assert ".aid-rebote" in bloque and "body::before" in bloque


# ─── tema aurora austral (por defecto desde la 2.2.0) ────────────────────────
def _luminancia(hexa: str) -> float:
    canales = []
    for i in (1, 3, 5):
        c = int(hexa[i:i + 2], 16) / 255
        canales.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    r, g, b = canales
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contraste(a: str, b: str) -> float:
    la, lb = sorted((_luminancia(a), _luminancia(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


SUPERFICIE_AURORA = "#0C1222"  # rgba(11,16,34,.80) sobre la noche: lo que ve el ojo


def test_aurora_no_lleva_figura_y_pinta_el_cielo():
    aurora = tema.TEMAS[tema.TEMA_AURORA]
    css = tema.variables(aurora)
    assert aurora.estilo == tema.ESTILO_AURORA and aurora.archivo is None
    assert "--aid-fondo: none;" in css
    assert tema.CIELO in css and tema.CUBIERTA not in css
    assert f"background-color: {tema.NOCHE};" in tema.CIELO


@pytest.mark.parametrize("color", [tema.AURORA_VERDE, tema.AURORA_VIOLETA, tema.AURORA_ROSA])
def test_los_colores_de_la_aurora_son_legibles_como_texto(color):
    """Las cifras van en degradado verde→violeta: AMBOS extremos deben pasar AA."""
    assert _contraste(color, SUPERFICIE_AURORA) >= 4.5


@pytest.mark.parametrize("clave, t", sorted(tema.TEMAS.items()))
def test_el_texto_de_los_botones_primarios_pasa_aa_en_todos_los_temas(clave, t):
    """Blanco sobre los acentos daba 1,3–3,4:1. La tinta oscura es la que se aplica."""
    assert _contraste(t.acento, tema.TINTA_SOBRE_ACENTO) >= 4.5, clave


def test_la_tinta_de_los_botones_va_en_la_primera_capa():
    """Trampa de capas: un `!important` SIN capa pierde contra el `!important` de la capa
    `quasar_importants`. Solo gana si se declara en la primera capa (`theme`)."""
    assert "@layer theme" in tema._CSS_CAPA_TEMA
    assert ".q-btn.bg-primary.text-white" in tema._CSS_CAPA_TEMA
    assert tema.TINTA_SOBRE_ACENTO in tema._CSS_CAPA_TEMA


@pytest.mark.parametrize("selector", [".aid-header", ".aid-drawer", ".aid-superficie",
                                      ".aid-tabla", ".aid-cifra"])
def test_aurora_redefine_el_cromo_y_las_superficies(selector):
    assert f"body.aid-aurora {selector}" in tema._CSS


@pytest.mark.parametrize("selector", [".aid-header {", ".aid-drawer {"])
def test_el_cromo_aurora_conserva_el_important_contra_bg_primary(selector):
    """Trampa (4) de CLAUDE.md: sin `!important` propio Quasar aplica `bg-primary`."""
    bloque = tema._CSS.split(f"body.aid-aurora {selector}", 1)[1].split("}", 1)[0]
    fondo = bloque.split("background", 1)[1].split(";", 1)[0]
    assert "!important" in fondo, f"{selector}: el fondo aurora perdería contra bg-primary"


def test_la_aurora_se_queda_quieta_con_movimiento_reducido():
    bloque = tema._CSS.split("prefers-reduced-motion", 1)[1].split("}", 2)[0]
    assert "body.aid-aurora::after" in bloque and "body.aid-aurora::before" in bloque


def test_la_aurora_anima_solo_transform_y_opacidad():
    """Las cortinas son una capa YA difuminada que se mueve con `transform`: es lo que
    el compositor anima sin repintar (barato en un móvil). Animar `filter` o
    `background-position` repintaría la capa entera en cada fotograma."""
    for nombre in ("aid-aurora", "aid-titilar"):
        # Hasta la siguiente regla `@` o el siguiente comentario: el cuerpo del keyframe.
        cuerpo = tema._CSS.split(f"@keyframes {nombre}", 1)[1].split("@", 1)[0].split("/*", 1)[0]
        propiedades = set(re.findall(r"([a-z-]+)\s*:", cuerpo))
        assert propiedades <= {"transform", "opacity"}, (nombre, propiedades)


# ─── gráficos: CSS de responsividad ──────────────────────────────────────────
@pytest.mark.parametrize("alto", ["s", "m", "l", "xl"])
def test_las_alturas_de_grafico_dependen_del_ancho(alto):
    bloque = tema._CSS.split(f".aid-alto-{alto}", 1)[1].split("}", 1)[0]
    assert "clamp(" in bloque and "vw" in bloque


def test_la_barra_de_plotly_se_oculta_en_tactil_salvo_en_pantalla_completa():
    bloque = tema._CSS.split("@media (hover: none)", 1)[1].split("/*", 1)[0]
    assert ".modebar-container" in bloque and ":not(:fullscreen)" in bloque


def test_la_pantalla_completa_tiene_respaldo_para_iphone():
    assert "aid-graf--max" in tema._CSS and "aid-graf--max" in tema._JS
    assert "webkitRequestFullscreen" in tema._JS


def test_el_drawer_es_responsivo():
    """`value=None` = `show-if-above` de Quasar: cerrado por debajo de 1024 px."""
    assert "left_drawer(value=None" in inspect.getsource(layout.shell)


def test_el_boton_de_pantalla_completa_no_flota_sobre_el_grafico():
    """Antes iba `absolute` arriba a la izquierda y pisaba título y barra de Plotly."""
    assert "position: absolute" not in tema._CSS.split(".aid-fsbtn", 1)[1].split("}", 1)[0]


def test_las_tarjetas_aurora_no_desenfocan_el_cielo_animado():
    """Con el fondo animado, `backdrop-filter` obliga a re-desenfocar cada tarjeta en cada
    fotograma (una captura completa a 360 px no terminaba en 30 s). Solo el cromo lo usa."""
    for selector in (".aid-superficie {", ".aid-tabla {"):
        bloque = tema._CSS.split(f"body.aid-aurora {selector}", 1)[1].split("}", 1)[0]
        assert "backdrop-filter: none" in bloque, selector


def test_la_hoja_no_deja_marcadores_sin_reemplazar():
    """Los colores entran a `_CSS` con `.replace("AV_", ...)`: un marcador que se olvida
    de reemplazar queda como CSS inválido y la regla entera se descarta EN SILENCIO."""
    assert not re.findall(r"\b[A-Z]{2,}_\b", tema._CSS)


def test_la_cabecera_del_upload_lleva_tinta_oscura():
    assert f".q-uploader__header {{ color: {tema.TINTA_SOBRE_ACENTO}; }}" in tema._CSS
