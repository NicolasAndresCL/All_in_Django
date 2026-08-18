"""
preparar_fondos.py — Pipeline de assets: FondosUI/ -> nicegui_ui/static/fondos/

Los PNG de origen no tienen canal alfa: traen el **damero gris de "fondo
transparente" horneado en los pixeles** (#FFFFFF/#EEEEEE). Puestos tal cual sobre
el negro de la UI se verian como un rectangulo claro, asi que hay que reconstruir
la transparencia.

No sirve un color-key ("todo lo casi-blanco es fondo"): borraria el logo blanco de
AoT, el craneo de la bandera y los blancos de Brook o Chopper. Se hace por
**conectividad**: solo es fondo el damero que toca el borde de la imagen, propagado
hacia adentro. Los blancos encerrados por el dibujo sobreviven.

De paso calcula los dos valores que la UI usa por personaje (`layout.TEMAS`):
- el **acento** (tono dominante ponderado por saturacion), y
- la **opacidad** de la marca de agua, compensada por el brillo medio de la figura:
  Brook (frac negro) necesita casi el doble que el sombrero de paja para leerse igual
  de presente. Con un valor unico, unos personajes quedan apagados y otros deslumbran.

Solo hace falta para REGENERAR los assets; la UI consume los PNG ya procesados.
    python scripts/preparar_fondos.py            # requiere pillow + numpy
"""

from __future__ import annotations

import colorsys
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

RAIZ = Path(__file__).resolve().parent.parent
ORIGEN = RAIZ / "FondosUI"
DESTINO = RAIZ / "nicegui_ui" / "static" / "fondos"
# La banda de la portada pinta 12 figuras a 84 px de alto: servir ahi los PNG completos
# seria descargar ~1,5 MB para mostrar miniaturas. Se genera una version pequena (2x
# para pantallas densas) que es lo que consume la banda.
MINIATURAS = DESTINO / "mini"
ALTO_MINIATURA = 168

# El damero es gris neutro y muy claro; el margen cubre el antialias del borde.
UMBRAL_CLARO = 228
TOLERANCIA_NEUTRO = 10

# Segunda pasada, mas laxa: las sombras suaves de la imagen (p. ej. bajo el Sunny) son
# gris semitransparente MEZCLADO con el damero, asi que no llegan a UMBRAL_CLARO y la
# pasada estricta las deja fuera. Solo se absorben si ya tocan fondo confirmado y siguen
# siendo neutras: el dibujo es cromatico, asi que no lo alcanza.
UMBRAL_CLARO_SUAVE = 196
TOLERANCIA_NEUTRO_SUAVE = 14


def _propagar(semilla: np.ndarray, candidato: np.ndarray) -> np.ndarray:
    """Crece `semilla` por 4-vecindad dentro de `candidato` hasta punto fijo."""
    fondo = semilla & candidato
    while True:
        crecido = fondo.copy()
        crecido[1:, :] |= fondo[:-1, :]
        crecido[:-1, :] |= fondo[1:, :]
        crecido[:, 1:] |= fondo[:, :-1]
        crecido[:, :-1] |= fondo[:, 1:]
        crecido &= candidato
        if np.array_equal(crecido, fondo):
            return fondo
        fondo = crecido


def _mascara_fondo(rgb: np.ndarray) -> np.ndarray:
    """True donde hay damero conectado con el borde (es decir, fondo de verdad)."""
    canal_max = rgb.max(axis=2).astype(np.int16)
    canal_min = rgb.min(axis=2).astype(np.int16)
    neutro = canal_max - canal_min

    # Semilla: el borde de la imagen. Desde ahi se propaga hacia adentro.
    borde = np.zeros(rgb.shape[:2], dtype=bool)
    borde[0, :] = borde[-1, :] = borde[:, 0] = borde[:, -1] = True

    estricto = (neutro <= TOLERANCIA_NEUTRO) & (canal_min >= UMBRAL_CLARO)
    fondo = _propagar(borde, estricto)

    suave = (neutro <= TOLERANCIA_NEUTRO_SUAVE) & (canal_min >= UMBRAL_CLARO_SUAVE)
    return _propagar(fondo, suave | fondo)


def _acento(rgb: np.ndarray, alfa: np.ndarray) -> str:
    """Color de acento de la imagen: tono dominante ponderado por saturacion*brillo.

    Se devuelve normalizado a alta saturacion y brillo para que funcione como color
    de interfaz sobre fondo negro (el tono viene del dibujo; el punch lo ponemos).
    """
    visibles = rgb[alfa > 128] / 255.0
    if not len(visibles):  # pragma: no cover - imagen vacia
        return "#2AAAFF"
    hsv = np.array([colorsys.rgb_to_hsv(*p) for p in visibles])
    tono, sat, val = hsv[:, 0], hsv[:, 1], hsv[:, 2]

    vivos = (sat > 0.35) & (val > 0.30)
    if vivos.sum() < 50:  # imagen casi monocroma (p. ej. el logo de AoT)
        vivos = sat > 0.12
    if not vivos.sum():  # pragma: no cover
        return "#2AAAFF"

    peso = sat[vivos] * val[vivos]
    hist, bordes = np.histogram(tono[vivos], bins=36, range=(0, 1), weights=peso)
    centro = (bordes[hist.argmax()] + bordes[hist.argmax() + 1]) / 2
    r, g, b = colorsys.hsv_to_rgb(centro, 0.78, 1.0)
    return f"#{int(r * 255):02X}{int(g * 255):02X}{int(b * 255):02X}"


# Brillo de referencia de la marca de agua y limites de opacidad.
#
# Las figuras deben VERSE (caras incluidas), no insinuarse: por eso el suelo es alto.
# La legibilidad no se defiende bajando la opacidad sino con los velos de las
# superficies con datos (tarjetas, tablas y campos llevan fondo casi opaco), asi que
# el texto nunca se apoya directamente sobre el dibujo.
PRESENCIA_OBJETIVO = 0.108
OPACIDAD_MIN, OPACIDAD_MAX = 0.36, 0.80


def _luminancia(rgb: np.ndarray) -> np.ndarray:
    c = np.asarray(rgb, dtype=float) / 255.0
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * c[..., 0] + 0.7152 * c[..., 1] + 0.0722 * c[..., 2]


def _opacidad(rgb: np.ndarray, alfa: np.ndarray) -> float:
    """Opacidad que iguala la PRESENCIA percibida de esta figura con la del resto.

    Se parte del brillo medio de sus pixeles visibles: cuanto mas oscura es la figura,
    mas opacidad necesita para leerse igual. El recorte superior es lo que protege el
    contraste del texto.
    """
    visibles = rgb[alfa > 128]
    if not len(visibles):  # pragma: no cover - imagen vacia
        return OPACIDAD_MAX
    media = float(_luminancia(visibles).mean())
    return round(min(OPACIDAD_MAX, max(OPACIDAD_MIN, PRESENCIA_OBJETIVO / media)), 2)


def procesar(ruta: Path) -> dict:
    rgb_img = Image.open(ruta).convert("RGB")
    rgb = np.asarray(rgb_img)

    alfa = np.where(_mascara_fondo(rgb), 0, 255).astype(np.uint8)
    # Erosion de 1 px: se come el halo blanco que deja el antialias contra el damero.
    alfa = np.asarray(Image.fromarray(alfa).filter(ImageFilter.MinFilter(3)))

    salida = Image.fromarray(np.dstack([rgb, alfa]), "RGBA")
    if recorte := salida.getbbox():  # quita los margenes vacios: mejora el encuadre
        salida = salida.crop(recorte)

    DESTINO.mkdir(parents=True, exist_ok=True)
    MINIATURAS.mkdir(parents=True, exist_ok=True)
    # Paleta de 255 colores + 1 para la transparencia: pesa ~3x menos que RGBA y el
    # canal alfa se conserva intacto (son dibujos planos, no fotografias).
    _guardar_png(salida, DESTINO / ruta.name)

    mini = salida.copy()
    mini.thumbnail((ALTO_MINIATURA * 2, ALTO_MINIATURA), Image.LANCZOS)
    _guardar_png(mini, MINIATURAS / ruta.name)

    return {"acento": _acento(rgb, alfa), "tamano": salida.size,
            "opacidad": _opacidad(rgb, alfa)}


def _guardar_png(img: Image.Image, destino: Path) -> None:
    img.quantize(colors=255, method=Image.Quantize.FASTOCTREE).save(destino, optimize=True)


def main() -> None:
    """Procesa todo y emite las lineas de `layout.TEMAS` listas para pegar: los valores
    de acento/opacidad se derivan de las imagenes, no se eligen a mano."""
    resumen = {}
    for ruta in sorted(ORIGEN.glob("*.png")):
        datos = procesar(ruta)
        resumen[ruta.stem] = datos
        print(f"{ruta.name:16} acento={datos['acento']}  "
              f"opacidad={datos['opacidad']:.2f}  "
              f"{datos['tamano'][0]}x{datos['tamano'][1]}")

    print("\n--- para layout.TEMAS ---")
    for nombre, datos in resumen.items():
        print(f'    "{nombre}": Tema("{nombre}.png", "{datos["acento"]}", '
              f'"{nombre.title()}", {datos["opacidad"]:.2f}),')
    print("\nPaleta:", json.dumps({n: d["acento"] for n, d in resumen.items()}, indent=2))


if __name__ == "__main__":
    main()
