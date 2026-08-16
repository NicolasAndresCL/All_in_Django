"""
Tests de la identidad visual por página (layout.IDENTIDAD).

Protegen invariantes que se rompen en silencio: un nombre de archivo mal escrito deja
la página sin fondo sin que falle nada, y dos páginas con el mismo acento anulan el
propósito del diseño (que cada sección se reconozca por su color).
"""

import re

import pytest

from nicegui_ui import layout

ESTATICOS = layout.__file__.replace("layout.py", "static/fondos")


def _ruta(archivo: str, mini: bool = False) -> str:
    import os
    return os.path.join(ESTATICOS, "mini" if mini else "", archivo)


@pytest.mark.parametrize("titulo", [nombre for _, _, nombre in layout.PAGINAS])
def test_cada_pagina_del_menu_tiene_identidad(titulo):
    """Toda entrada del menú debe estar en IDENTIDAD: si no, cae al fondo por defecto
    y la página queda visualmente huérfana."""
    assert titulo in layout.IDENTIDAD


@pytest.mark.parametrize("archivo", sorted(
    {a for a, _ in layout.IDENTIDAD.values()} | set(layout.TRIPULACION)
    | {layout.MARCA.rsplit("/", 1)[-1]}))
def test_las_imagenes_referenciadas_existen(archivo):
    import os
    assert os.path.isfile(_ruta(archivo)), f"falta {archivo} en static/fondos/"


@pytest.mark.parametrize("archivo", sorted(layout.TRIPULACION))
def test_la_banda_usa_miniaturas_existentes(archivo):
    import os
    assert os.path.isfile(_ruta(archivo, mini=True)), f"falta la miniatura de {archivo}"


def test_los_acentos_son_distintos_entre_paginas():
    """El color es lo que distingue una sección de otra; repetirlo rompe el sistema."""
    acentos = [acento for _, acento in layout.IDENTIDAD.values()]
    assert len(set(acentos)) == len(acentos), f"acentos repetidos: {acentos}"


@pytest.mark.parametrize("titulo, acento", [(t, a) for t, (_, a) in layout.IDENTIDAD.items()])
def test_los_acentos_son_hex_validos(titulo, acento):
    assert re.fullmatch(r"#[0-9A-F]{6}", acento), f"{titulo}: {acento}"


def test_identidad_devuelve_url_servible_y_acento():
    url, acento = layout.identidad("Notas")
    assert url == f"{layout.FONDOS_URL}/robin.png"
    assert acento == layout.IDENTIDAD["Notas"][1]


def test_identidad_cae_al_valor_por_defecto_para_una_pagina_desconocida():
    archivo, acento = layout.IDENTIDAD_POR_DEFECTO
    assert layout.identidad("Pagina Inventada") == (f"{layout.FONDOS_URL}/{archivo}", acento)
