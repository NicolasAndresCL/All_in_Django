"""
Tests del sistema visual (`nicegui_ui.tema`).

Protegen invariantes que se rompen en silencio: un nombre de archivo mal escrito deja
la página sin fondo sin que falle nada, dos páginas con el mismo acento anulan el
propósito del diseño, y una opacidad fuera de rango o apaga la figura o rompe el
contraste con el texto.
"""

import os
import re

import pytest

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
