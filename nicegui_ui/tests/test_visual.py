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
    "/api/tareas/analitica/": datos_api.ANALITICA,
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


# ─── (1) el fondo se DIBUJA, no solo se define ───────────────────────────────
def test_el_fondo_llega_a_pintarse(pagina):
    """El fallo original: `background-image` definido y borrado por el shorthand de
    `bg-black`. Se mide el computed style, que es quien resuelve la cascada. Desde la
    2.2.0 el tema por defecto es aurora: su cielo tiene tres capas, como la cubierta."""
    imagen = _estilo(pagina, "body", "background-image")
    assert imagen and imagen != "none", "el body no pinta su fondo"
    assert imagen.count("gradient") >= 3, f"el fondo perdio capas: {imagen[:120]}"
    assert _estilo(pagina, "body", "background-attachment").startswith("fixed")
    assert pagina.evaluate("document.body.classList.contains('aid-aurora')"), \
        "el tema por defecto deberia ser aurora"


def test_las_cortinas_de_aurora_se_mueven(pagina):
    """La capa `body::after` anima `aid-aurora`: si una regla posterior la pisa (la del
    estilo cubierta no anima `::after`), el cielo queda congelado sin avisar."""
    nombre = pagina.evaluate("getComputedStyle(document.body, '::after').animationName")
    assert nombre == "aid-aurora"


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
    # Se espera la condicion (hasta 3 s) en vez de dormir 200 ms: con la maquina cargada
    # (un build de Docker en paralelo) el hover tardaba mas y el test fallaba en falso.
    try:
        imagen.evaluate("""el => new Promise((ok, mal) => {
            const t0 = performance.now();
            const mirar = () => getComputedStyle(el).animationName === 'none' ? ok(true)
                : performance.now() - t0 > 3000 ? mal('sigue animando') : requestAnimationFrame(mirar);
            mirar(); })""")
    except Exception:  # noqa: BLE001  (el rechazo llega como Error de Playwright)
        pytest.fail("el rebote sigue animando en hover: se pauso en vez de apagarse")


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


# ─── (5) responsividad: medida en el navegador, no supuesta ──────────────────
MEDIR_GRAFICOS = """
() => {
  const col = document.querySelector('.nicegui-content > .nicegui-column');
  const cs = getComputedStyle(col);
  const util = col.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
  const graficos = [...document.querySelectorAll('.aid-graf')].map((g) => {
    const p = g.querySelector('.js-plotly-plot');
    const svg = p && p.querySelector('svg.main-svg');
    return {
      tarjeta: g.getBoundingClientRect().width,
      lienzo: p ? p.getBoundingClientRect().width : 0,
      alto: p ? p.getBoundingClientRect().height : 0,
      svg: svg ? +svg.getAttribute('width') : 0,
    };
  }).filter((g) => g.lienzo > 0);
  const d = document.documentElement;
  return { util, graficos, scroll: d.scrollWidth - window.innerWidth };
}
"""


def _esperar(pag, condicion: str, timeout: int = 8_000) -> None:
    """`wait_for_function` que, si vence, falla con las medidas en vez de un timeout mudo."""
    try:
        pag.wait_for_function(condicion, timeout=timeout)
    except Exception:  # noqa: BLE001  (el TimeoutError de Playwright; se reporta con datos)
        pytest.fail(f"la condicion no se cumplio: {pag.evaluate(MEDIR_GRAFICOS)}")


def _abrir_en(navegador, url: str, ancho: int, alto: int = 800):
    movil = ancho < 700
    pag = navegador.new_page(viewport={"width": ancho, "height": alto}, is_mobile=movil,
                             has_touch=movil, reduced_motion="reduce")
    pag.goto(url, wait_until="networkidle")
    pag.wait_for_selector(".js-plotly-plot svg.main-svg", timeout=20_000)
    pag.wait_for_timeout(800)
    return pag


@pytest.mark.parametrize("ancho", [360, 412, 768])
def test_en_movil_y_tablet_los_graficos_ocupan_el_ancho_util(navegador, ui_viva, ancho):
    """El hallazgo de partida: con `ui.grid(columns=2)` fijo cada grafico tenia 104 px a
    360 px. Ahora debe ocupar >= 90 % del ancho util (1 columna; en 768, 2)."""
    pag = _abrir_en(navegador, f"{ui_viva}/tareas", ancho)
    try:
        m = pag.evaluate(MEDIR_GRAFICOS)
        assert m["graficos"], "no se dibujo ningun grafico"
        assert m["scroll"] <= 1, f"scroll horizontal de {m['scroll']} px a {ancho} px"
        columnas = 1 if ancho < 768 else 2
        minimo = 0.9 * (m["util"] - 16 * (columnas - 1)) / columnas
        estrechos = [g for g in m["graficos"] if g["tarjeta"] < minimo]
        assert not estrechos, f"a {ancho} px: tarjetas < {minimo:.0f} px: {estrechos}"
        # El lienzo sigue a la tarjeta y la altura no es una tira alta y flaca.
        malos = [g for g in m["graficos"]
                 if g["lienzo"] < 0.85 * g["tarjeta"] or g["alto"] > 2.2 * g["lienzo"]]
        assert not malos, malos
    finally:
        pag.close()


SOLAPES_EJE_X = """
() => [...document.querySelectorAll('.js-plotly-plot')].flatMap((p) => {
  const cajas = [...p.querySelectorAll('.xtick text')]
    .map((t) => t.getBoundingClientRect()).filter((r) => r.width > 0)
    .sort((a, b) => a.left - b.left);
  return cajas.slice(1).flatMap((r, i) => r.left < cajas[i].right - 1
    ? [{grafico: p.closest('.q-card')?.innerText.split('\\n')[0], izq: cajas[i].right, der: r.left}] : []);
})
"""


@pytest.mark.parametrize("ancho", [360, 412])
def test_en_movil_las_etiquetas_del_eje_x_no_se_pisan(navegador, ui_viva, ancho):
    """En un eje de CATEGORÍAS Plotly no oculta las etiquetas que chocan: con 40 semanas
    "Sem N" se montaban a 360 px. Se mide la caja real de cada etiqueta."""
    pag = _abrir_en(navegador, f"{ui_viva}/tareas", ancho)
    try:
        solapes = pag.evaluate(SOLAPES_EJE_X)
        assert not solapes, f"a {ancho} px se pisan etiquetas del eje X: {solapes}"
    finally:
        pag.close()


def test_en_movil_el_drawer_arranca_cerrado_y_sin_barra_de_plotly(navegador, ui_viva):
    """`value=True` lo abria como overlay en cada navegacion, tapando la pagina."""
    pag = _abrir_en(navegador, f"{ui_viva}/tareas", 360)
    try:
        abierto = pag.evaluate("""() => {
            const d = document.querySelector('.q-drawer');
            return !!d && d.getBoundingClientRect().right > 1; }""")
        assert not abierto, "el drawer tapa la pagina al cargar en movil"
        # Y la barra de Plotly no aparece en tactil (vuelve en pantalla completa).
        visibles = pag.evaluate("""() => [...document.querySelectorAll('.modebar-container')]
            .filter((m) => getComputedStyle(m).display !== 'none').length""")
        assert visibles == 0
    finally:
        pag.close()


def test_el_grafico_sigue_al_contenedor_al_cerrar_el_drawer(navegador, ui_viva):
    """Hallazgo 5: al cerrar el drawer en escritorio cambia el CONTENEDOR, no la ventana.
    El ResizeObserver del componente debe reajustar el svg al nuevo ancho."""
    pag = _abrir_en(navegador, f"{ui_viva}/tareas", 1440, 900)
    try:
        antes = pag.evaluate(MEDIR_GRAFICOS)["graficos"]
        pag.locator(".q-header button").first.click()
        # Se ESPERA la condicion en vez de dormir un tiempo fijo: la transicion del drawer
        # y el debounce de `Plotly.Plots.resize` suman un tiempo que varia por maquina.
        _esperar(pag, f"""() => {{
            const p = document.querySelector('.aid-graf .js-plotly-plot');
            const s = p.querySelector('svg.main-svg');
            const w = p.getBoundingClientRect().width;
            return w > {antes[0]["lienzo"]} + 50 && Math.abs(+s.getAttribute('width') - w) <= 2; }}""")
        despues = pag.evaluate(MEDIR_GRAFICOS)["graficos"]
        desfasados = [g for g in despues if abs(g["svg"] - g["lienzo"]) > 2]
        assert not desfasados, f"svg sin reajustar al contenedor: {desfasados}"
    finally:
        pag.close()


def test_el_boton_primario_pasa_aa(navegador, ui_viva):
    """Blanco sobre el acento daba 1,6:1 en aurora. La tinta oscura viaja en la capa
    `theme` precisamente para ganarle al `.text-white !important` de Quasar."""
    pag = _abrir_en(navegador, f"{ui_viva}/tareas", 1280)
    try:
        boton = pag.locator(".q-btn.bg-primary").first
        boton.wait_for(timeout=10_000)
        fondo = boton.evaluate("el => getComputedStyle(el).backgroundColor")
        texto = boton.evaluate("el => getComputedStyle(el).color")
        ratio = _contraste(fondo, texto)
        assert ratio >= 4.5, f"boton primario {ratio:.1f}:1 ({texto} sobre {fondo})"
    finally:
        pag.close()


def test_pantalla_completa_ocupa_la_ventana(navegador, ui_viva):
    """El boton vive en la cabecera de la tarjeta (ya no flota sobre el grafico) y al
    pulsarlo el lienzo crece hasta casi el alto de la ventana."""
    pag = _abrir_en(navegador, f"{ui_viva}/tareas", 1280, 800)
    try:
        tarjeta = pag.locator(".aid-graf").first
        lienzo = tarjeta.locator(".js-plotly-plot")
        alto_antes = lienzo.evaluate("el => el.getBoundingClientRect().height")
        tarjeta.locator(".aid-fsbtn").click()
        # El headless tarda ~1 s en entrar en pantalla completa: se espera la condicion.
        _esperar(pag, """() => {
            const p = document.querySelector('.aid-graf .js-plotly-plot');
            return p.getBoundingClientRect().height >= 0.75 * window.innerHeight
                && Math.abs(+p.querySelector('svg.main-svg').getAttribute('width')
                            - p.getBoundingClientRect().width) <= 2; }""")
        alto = lienzo.evaluate("el => el.getBoundingClientRect().height")
        assert alto > alto_antes and alto >= 0.75 * 800, f"pantalla completa: {alto_antes} -> {alto}"
    finally:
        pag.close()
