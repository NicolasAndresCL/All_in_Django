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
@pytest.mark.parametrize("clave, t", sorted(tema.TEMAS.items()))
def test_cada_tema_apunta_a_imagenes_existentes(clave, t):
    assert os.path.isfile(_ruta(t.archivo)), f"{clave}: falta {t.archivo}"
    assert os.path.isfile(_ruta(t.archivo, mini=True)), f"{clave}: falta su miniatura"


@pytest.mark.parametrize("clave, t", sorted(tema.TEMAS.items()))
def test_cada_tema_tiene_acento_hex_y_opacidad_util(clave, t):
    assert re.fullmatch(r"#[0-9A-F]{6}", t.acento), f"{clave}: acento {t.acento}"
    assert OPACIDAD_MIN <= t.opacidad <= OPACIDAD_MAX, f"{clave}: opacidad {t.opacidad}"
    assert t.etiqueta.strip(), f"{clave}: sin etiqueta para el selector"


def test_hay_un_tema_por_cada_imagen_disponible():
    """Si se añade un PNG al pipeline, debe aparecer en el selector: si no, queda
    procesado y pesando en la imagen Docker pero inalcanzable."""
    en_disco = {f for f in os.listdir(ESTATICOS) if f.endswith(".png")}
    en_temas = {t.archivo for t in tema.TEMAS.values()}
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
    assert tema.tema_activo("Notas") is tema.TEMAS["robin"]


def test_una_pagina_desconocida_cae_al_tema_por_defecto():
    assert tema.tema_activo("Pagina Inventada") is tema.TEMAS[tema.IDENTIDAD_POR_DEFECTO]


def test_sin_contexto_de_usuario_el_tema_es_auto():
    """`app.storage.user` exige contexto de petición. Fuera de él (tests, importación)
    no debe reventar: la respuesta correcta es Auto."""
    assert tema.tema_elegido() == tema.TEMA_AUTO


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
