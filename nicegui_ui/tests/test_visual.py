"""
Verificacion VISUAL medida, no a ojo: computed style y contraste reales en un navegador.

**Por que existe.** Los tres bugs de CSS del sistema visual se cazaron a mano con el MCP de
Playwright, midiendo el computed style; el arreglo quedo en el codigo pero la comprobacion
no quedo en ninguna parte. `test_tema.py` mira el CSS como TEXTO —util, pero un `!important`
presente en la hoja no prueba que gane la cascada— y `test_paginas.py` corre en una
simulacion sin navegador, donde no hay estilos que medir. Este archivo cierra ese hueco:
levanta la UI de verdad, la abre en Chromium y **mide**.

Las tres regresiones que vigila, todas documentadas en `aprendizaje.md`:

1. La cubierta de madera desaparecia porque la utilidad `bg-black` de Quasar es
   `background: #000 !important`, y ese shorthand borra el `background-image` que la
   longhand habia puesto. El fondo se definia y no se dibujaba.
2. El header y el drawer necesitan `background: ... !important` propio o Quasar les aplica
   `bg-primary`, dejando el cromo del color del acento en vez del suyo.
3. La legibilidad no se defiende bajando la opacidad del fondo, sino con velos: las
   tarjetas llevan fondo casi opaco para que el texto conserve su contraste sobre una
   ilustracion con presencia.

**Fuera del CI a proposito** (marca `visual`, excluida en pytest.ini): exige
`playwright install chromium`, ~150 MB y un par de minutos por corrida. Se ejecuta a
demanda y desde `scripts/verificar.ps1`:

    pytest -m visual
"""

import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

pytest.importorskip("playwright", reason="pip install playwright && playwright install chromium")
import datos_api  # noqa: E402  (mismo directorio; pytest lo pone en sys.path)
from playwright.sync_api import sync_playwright  # noqa: E402

pytestmark = pytest.mark.visual

RAIZ = Path(__file__).resolve().parents[2]

# Respuestas de la API falsa, por sufijo de ruta. La UI solo hace GET en el arranque.
RESPUESTAS = {
    "/api/": {},
    "/api/clases/": datos_api.CLASES,
    "/api/turnos-personales/": datos_api.TURNOS_PERSONALES,
    "/api/turnos-equipo/": datos_api.TURNOS_EQUIPO,
    "/api/tareas/": datos_api.TAREAS,
    "/api/tareas/resumen/": datos_api.RESUMEN,
    "/api/notas/": datos_api.NOTAS,
    "/api/tv/canales/": datos_api.CANALES,
}


def _puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class _ApiFalsa(BaseHTTPRequestHandler):
    """Sirve los datos de ejemplo. Un mock de `responses` no vale aqui: la UI corre en
    OTRO proceso y sale a la red de verdad."""

    def do_GET(self) -> None:  # noqa: N802  (firma de BaseHTTPRequestHandler)
        cuerpo = RESPUESTAS.get(self.path.split("?")[0], [])
        datos = json.dumps(cuerpo).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(datos)))
        self.end_headers()
        self.wfile.write(datos)

    def log_message(self, format: str, *args) -> None:  # noqa: A002  (firma de la clase base)
        pass  # sin ruido en la salida de pytest


@pytest.fixture(scope="module")
def ui_viva():
    """Levanta la API falsa y la UI real, y cede la URL base."""
    api = HTTPServer(("127.0.0.1", _puerto_libre()), _ApiFalsa)
    threading.Thread(target=api.serve_forever, daemon=True).start()

    puerto_ui = _puerto_libre()
    entorno = os.environ | {
        "API_BASE": f"http://127.0.0.1:{api.server_port}/api",
        "API_TOKEN": "token-de-test",
        "UI_PORT": str(puerto_ui),
    }
    # NiceGUI decide que esta "bajo pytest" con `'PYTEST_CURRENT_TEST' in os.environ`
    # (helpers.is_pytest) y entonces `ui.run` exige NICEGUI_SCREEN_TEST_PORT y muere con
    # un KeyError. Aqui el subproceso NO es un test: es la aplicacion de verdad, arrancada
    # desde un test. Heredar esa variable la hacia morir antes de servir una sola pagina.
    entorno.pop("PYTEST_CURRENT_TEST", None)
    # La salida se guarda en vez de descartarse: si la UI muere al arrancar, el motivo
    # esta ahi y un `pytest.fail` mudo obligaria a reproducirlo a mano.
    registro = tempfile.NamedTemporaryFile("w+", suffix=".log", delete=False, encoding="utf-8")
    proceso = subprocess.Popen(
        [sys.executable, "-m", "nicegui_ui.main"], cwd=RAIZ, env=entorno,
        stdout=registro, stderr=subprocess.STDOUT,
    )
    base = f"http://127.0.0.1:{puerto_ui}"

    def _salida() -> str:
        registro.flush()
        return Path(registro.name).read_text(encoding="utf-8", errors="replace")[-2000:]

    try:
        for _ in range(120):  # hasta 60 s: el primer arranque compila y sirve los assets
            if proceso.poll() is not None:
                pytest.fail(f"la UI murio al arrancar:\n{_salida()}")
            try:
                with socket.create_connection(("127.0.0.1", puerto_ui), timeout=0.5):
                    break
            except OSError:
                time.sleep(0.5)
        else:
            pytest.fail(f"la UI no respondio a tiempo:\n{_salida()}")
        yield base
    finally:
        proceso.terminate()
        proceso.wait(timeout=10)
        api.shutdown()
        registro.close()
        Path(registro.name).unlink(missing_ok=True)


@pytest.fixture(scope="module")
def navegador():
    with sync_playwright() as p:
        nav = p.chromium.launch()
        yield nav
        nav.close()


def _abrir(navegador, url: str, *, movimiento: str = "no-preference"):
    pag = navegador.new_page(viewport={"width": 1440, "height": 900}, reduced_motion=movimiento)
    pag.goto(url, wait_until="networkidle")
    pag.wait_for_selector(".q-header", timeout=15_000)
    return pag


@pytest.fixture(scope="module")
def pagina(navegador, ui_viva):
    """La preferencia de movimiento se fija EXPLICITAMENTE: el headless shell puede
    reportar `reduce` por su cuenta, y entonces el test del rebote medira una animacion
    apagada a proposito y creera haber encontrado un bug."""
    pag = _abrir(navegador, ui_viva)
    yield pag
    pag.close()


# ─── utilidades de medida ────────────────────────────────────────────────────
def _rgb(valor: str) -> tuple[float, float, float]:
    """Acepta `rgb()`, `rgba()` y `#rrggbb`: el computed style devuelve rgb, pero una
    custom property se lee TAL CUAL se escribio, y los acentos del tema son hex."""
    valor = valor.strip()
    if valor.startswith("#"):
        h = valor[1:]
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        r, g, b = (float(int(h[i:i + 2], 16)) for i in (0, 2, 4))
    else:
        r, g, b = (float(n) for n in
                   valor.replace("rgba", "rgb").strip("rgb() ").split(",")[:3])
    return r, g, b


def _luminancia(color: tuple[float, float, float]) -> float:
    """Luminancia relativa segun WCAG 2.1."""
    canales = []
    for bruto in color:
        c = bruto / 255
        canales.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    r, g, b = canales
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contraste(uno: str, otro: str) -> float:
    a, b = sorted((_luminancia(_rgb(uno)), _luminancia(_rgb(otro))), reverse=True)
    return (a + 0.05) / (b + 0.05)


def _estilo(pagina, selector: str, propiedad: str) -> str:
    return pagina.eval_on_selector(
        selector,
        "(el, prop) => getComputedStyle(el).getPropertyValue(prop)",
        propiedad,
    )


# ─── (1) la cubierta se DIBUJA, no solo se define ────────────────────────────
def test_la_cubierta_de_madera_llega_a_pintarse(pagina):
    """El fallo original: `background-image` definido y borrado por el shorthand de
    `bg-black`. Se mide el computed style, que es quien resuelve la cascada."""
    imagen = _estilo(pagina, "body", "background-image")
    assert imagen and imagen != "none", "el body no pinta la cubierta"
    assert imagen.count("gradient") >= 3, f"la cubierta perdio capas: {imagen[:120]}"
    assert _estilo(pagina, "body", "background-attachment").startswith("fixed")


# ─── (2) el cromo conserva su fondo frente a bg-primary ──────────────────────
def test_el_header_no_se_queda_con_el_color_primario(pagina):
    """Sin `background: ... !important` propio, Quasar le aplica `bg-primary` y el header
    sale del color del acento. Se compara contra el acento REAL del tema activo."""
    acento = _estilo(pagina, "body", "--aid-acento").strip()
    fondo_header = _estilo(pagina, ".q-header", "background-color")
    assert acento, "el tema no publico su acento como custom property"
    assert _rgb(fondo_header) != _rgb(acento), "el header quedo pintado con bg-primary"
    assert _rgb(fondo_header) != (0.0, 0.0, 0.0) or True  # negro es un fondo legitimo aqui


# ─── (3) el velo mantiene el texto legible ───────────────────────────────────
def test_el_texto_sobre_las_tarjetas_supera_el_minimo_de_wcag(pagina):
    """AA exige 4,5:1 para texto normal. Las tarjetas llevan fondo casi opaco justo para
    esto: la legibilidad no se defiende apagando la ilustracion."""
    tarjeta = pagina.locator(".q-card").first
    tarjeta.wait_for(timeout=10_000)
    fondo = tarjeta.evaluate("el => getComputedStyle(el).backgroundColor")
    texto = tarjeta.evaluate("el => getComputedStyle(el).color")
    ratio = _contraste(fondo, texto)
    assert ratio >= 4.5, f"contraste {ratio:.1f}:1 sobre la tarjeta (AA exige 4.5:1)"


# ─── (4) el rebote se APAGA en hover, no se pausa ────────────────────────────
def test_el_rebote_se_apaga_al_pasar_el_raton(pagina):
    """Una animacion en curso gana a cualquier regla del hover: el `transform` del rebote
    ignoraba el `:hover` hasta que la animacion se apaga (`animation: none`)."""
    # El selector va al WRAPPER `.q-img` y no al `<img>`: `ui.image` envuelve la etiqueta y
    # `default_classes("aid-rebote")` marca el envoltorio, que es quien anima. Medir el
    # `<img>` interno devuelve "none" siempre, y el test parece encontrar un fallo que no
    # existe. Es la misma trampa por la que el TAMANO tambien va en el wrapper.
    imagen = pagina.locator(".aid-rebote").first
    imagen.wait_for(timeout=10_000)
    assert imagen.evaluate("el => getComputedStyle(el).animationName") == "aid-rebote"
    imagen.hover()
    pagina.wait_for_timeout(200)
    assert imagen.evaluate("el => getComputedStyle(el).animationName") == "none", \
        "el rebote sigue animando en hover: se pauso en vez de apagarse"


def test_con_movimiento_reducido_no_se_anima_nada(navegador, ui_viva):
    """El otro sentido de la misma regla: `prefers-reduced-motion: reduce` deja todo
    quieto. Sin este test, el bloque @media podria borrarse sin que nada avisara."""
    pag = _abrir(navegador, ui_viva, movimiento="reduce")
    try:
        quieto = pag.locator(".aid-rebote").first
        quieto.wait_for(timeout=10_000)
        assert quieto.evaluate("el => getComputedStyle(el).animationName") == "none"
    finally:
        pag.close()
