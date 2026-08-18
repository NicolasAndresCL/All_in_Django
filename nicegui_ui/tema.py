"""
tema.py — Sistema visual de la UI (personalización GLOBAL, no elemento por elemento).

Sigue la guía oficial de NiceGUI (`nicegui/llms.md`, "The Golden Rule – Python First"):
la personalización se hace de arriba abajo y el CSS crudo es el último recurso.

    1. `aplicar_defaults()`  — `default_props` / `default_classes` / `default_style` por
       tipo de elemento. Se llama UNA vez al arrancar y afecta a todo lo que se cree
       después, así que las vistas ya no repiten `.props('outlined dense')` por campo.
    2. `ui.query('body')`    — estilado a nivel de página. La guía marca explícitamente
       `add_head_html('<style>body{...}</style>')` como ANTIPATRÓN para esto.
    3. Clases **Tailwind** en los elementos: es la herramienta primaria de estilo.
    4. `ui.add_head_html`    — SOLO para lo que la API de Python no puede expresar: los
       pseudo-elementos `body::before/::after` con `mask-image` y `drop-shadow` que
       dibujan la marca de agua y su aura. No hay clase Tailwind ni prop de Quasar para
       eso. Se inyecta UNA vez al arrancar, no en cada render de página.

Identidad visual, en dos niveles:

    - **Tema por personaje** (`TEMAS`): lo elige el usuario y manda en toda la app.
      Se guarda en `app.storage.user`, que es **por usuario/navegador**. NO se usa
      `app.storage.general`: ese ámbito es "todos los usuarios" y persiste en un archivo
      dentro del proyecto, así que el tema se filtraba a cualquier otra instancia
      levantada sobre la misma carpeta (incluida la del propio Nicolás).
    - **Identidad por página** (`IDENTIDAD`): el reparto semántico que manda en "Auto".
"""

from __future__ import annotations

from dataclasses import dataclass

from nicegui import app, ui

# ─── Paleta base: VS Code Dark High Contrast ─────────────────────────────────
FONDO = "#000000"        # editor.background (negro puro)
BORDE = "#6FC3DF"        # contrastBorder (cian)
FOCO = "#F38518"         # focusBorder (naranja)

# Prefijo con el que `main.py` publica nicegui_ui/static/fondos/.
FONDOS_URL = "/fondos"

# Emblema de la app en el drawer.
MARCA = f"{FONDOS_URL}/mugiwara.png"

# Plantilla Plotly acorde al tema oscuro.
PLOTLY_TEMPLATE = "plotly_dark"


@dataclass(frozen=True)
class Tema:
    """Un personaje como tema completo: figura, color de aura y su opacidad.

    `opacidad` no es un número a ojo: `scripts/preparar_fondos.py` mide el brillo medio
    de los píxeles visibles de cada PNG y compensa. Las figuras oscuras (Brook de frac
    negro, Sanji, Zoro) necesitan mucha más opacidad que un emblema claro para leerse
    con la misma presencia; con un valor único unas quedan apagadas y otras deslumbran.
    """

    archivo: str
    acento: str
    etiqueta: str
    opacidad: float


TEMA_AUTO = "auto"

TEMAS: dict[str, Tema] = {
    "Luffy": Tema("Luffy.png", "#FF4838", "Luffy", 0.49),
    "zoro": Tema("zoro.png", "#38FF8A", "Zoro", 0.62),
    "nami": Tema("nami.png", "#FF6938", "Nami", 0.36),
    "usopp": Tema("usopp.png", "#FFCD38", "Usopp", 0.36),
    "sanji": Tema("sanji.png", "#FFCD38", "Sanji", 0.75),
    "chopper": Tema("chopper.png", "#38CDFF", "Chopper", 0.36),
    "robin": Tema("robin.png", "#FF3898", "Robin", 0.36),
    "franky": Tema("franky.png", "#FF8A38", "Franky", 0.36),
    "brook": Tema("brook.png", "#388AFF", "Brook", 0.78),
    "jinbe": Tema("jinbe.png", "#FF4838", "Jinbe", 0.53),
    "sunny": Tema("sunny.png", "#FF4838", "Thousand Sunny", 0.36),
    "onePiece": Tema("onePiece.png", "#38CDFF", "Tripulación", 0.40),
    "mugiwara": Tema("mugiwara.png", "#FFCD38", "Jolly Roger", 0.36),
    "sombrero": Tema("sombrero.png", "#FFCD38", "Sombrero", 0.36),
    "mikasa": Tema("mikasa.png", "#FF8A38", "Mikasa", 0.39),
    "aot": Tema("aot.png", "#38ACFF", "Survey Corps", 0.36),
}

# Página → clave de TEMAS. Reparto semántico, no decorativo:
#   Calendario → Nami (navegante), LiveOps → Jinbe (timonel), Tareas → Zoro (disciplina),
#   Notas → Robin (arqueóloga), TV → Brook (músico), Apagado → el sombrero colgado.
IDENTIDAD = {
    "Inicio": "onePiece",
    "Calendario": "nami",
    "LiveOps Equipo": "jinbe",
    "Registro de Tareas": "zoro",
    "Notas": "robin",
    "TV Chile": "brook",
    "Apagado": "sombrero",
}
IDENTIDAD_POR_DEFECTO = "mugiwara"

# Banda de la portada: solo personajes y el barco (los emblemas, a ese tamaño, leen
# como una mancha en vez de como una figura).
TRIPULACION = ["Luffy.png", "zoro.png", "nami.png", "usopp.png", "sanji.png",
               "chopper.png", "robin.png", "franky.png", "brook.png", "jinbe.png",
               "mikasa.png", "sunny.png"]


# ─── Resolución del tema ─────────────────────────────────────────────────────
def url_fondo(tema: Tema) -> str:
    return f"{FONDOS_URL}/{tema.archivo}"


def tema_de_pagina(titulo: str) -> Tema:
    return TEMAS[IDENTIDAD.get(titulo, IDENTIDAD_POR_DEFECTO)]


def tema_elegido() -> str:
    """Clave del tema fijado por ESTE usuario, o TEMA_AUTO.

    `app.storage.user` exige `storage_secret` y un contexto de petición; fuera de él
    (tests unitarios, importación) no hay usuario y la respuesta correcta es "Auto".
    """
    try:
        return app.storage.user.get("tema", TEMA_AUTO)
    except (RuntimeError, AttributeError):
        return TEMA_AUTO


def fijar_tema(clave: str) -> None:
    app.storage.user["tema"] = clave


def tema_activo(titulo: str) -> Tema:
    """El tema que se aplica: el elegido a mano si lo hay, si no el de la página."""
    clave = tema_elegido()
    return TEMAS[clave] if clave in TEMAS else tema_de_pagina(titulo)


def variables(tema: Tema) -> str:
    """Custom properties del tema, como cadena para `ui.query('body').style(...)`.

    Definirlas sobre `body` —y no en un `<style>` inyectado por página— es lo que
    permite cambiar de tema sin acumular bloques de CSS en el head.
    """
    return (f"--aid-acento: {tema.acento};"
            f"--aid-fondo: url('{url_fondo(tema)}');"
            f"--aid-opacidad: {tema.opacidad};")


# ─── 1. Defaults globales por tipo de elemento ───────────────────────────────
def aplicar_defaults() -> None:
    """Personalización global; se llama UNA vez al arrancar (`main.py`).

    `default_props`/`default_classes` son *classmethods*: afectan a cada instancia
    creada a partir de ese momento, así que sustituyen al `.props(...)` repetido en
    todas las vistas. Al ser estado de proceso, NO deben llamarse por página.
    """
    # Formularios: mismo aspecto en toda la app sin repetirlo campo a campo.
    for campo in (ui.input, ui.number, ui.select, ui.textarea):
        campo.default_props("outlined dense")
    ui.button.default_props("unelevated no-caps")
    ui.checkbox.default_props("dense")

    # Superficies: mismo lenguaje visual para tarjetas y tablas.
    ui.card.default_classes("aid-superficie rounded-xl")
    ui.table.default_props("dense flat virtual-scroll")
    ui.table.default_classes("aid-tabla w-full rounded-lg")
    ui.separator.default_classes("aid-separador")
    ui.image.default_props("no-spinner fit=contain")
    ui.tooltip.default_classes("text-xs")


# ─── 4. CSS global: solo lo que la API de Python no puede expresar ───────────
_CSS = """
<style>
:root { --aid-borde: BORDE_; --aid-foco: FOCO_; }

/* Capa de fondo: dos pseudo-elementos fijos detrás de todo. No hay equivalente en
   Tailwind ni props de Quasar para `mask-image` + `drop-shadow` sobre ::before. */
body::before, body::after {
    content: ""; position: fixed; inset: 0; pointer-events: none; z-index: 0;
}
body::before {
    background-image: var(--aid-fondo);
    background-repeat: no-repeat;
    background-position: right 1.5vw bottom -4vh;
    background-size: auto 84vh;
    opacity: var(--aid-opacidad, 0.6);
    /* EL AURA: el drop-shadow se calcula sobre el alfa de la figura, así que el halo
       sigue su silueta en vez de ser un rectángulo de color. */
    filter: saturate(1.15)
            drop-shadow(0 0 16px color-mix(in srgb, var(--aid-acento) 90%, transparent))
            drop-shadow(0 0 60px color-mix(in srgb, var(--aid-acento) 65%, transparent))
            drop-shadow(0 0 130px color-mix(in srgb, var(--aid-acento) 40%, transparent));
    /* Viñeta amplia: la figura se ve entera (cara incluida) y solo se disuelve al
       acercarse a la zona de contenido. */
    -webkit-mask-image: radial-gradient(ellipse 96% 100% at 82% 58%,
                                        #000 62%, rgba(0,0,0,.75) 82%, transparent 98%);
    mask-image: radial-gradient(ellipse 96% 100% at 82% 58%,
                                #000 62%, rgba(0,0,0,.75) 82%, transparent 98%);
}
body::after {
    background:
        radial-gradient(820px 820px at 80% 56%,
                        color-mix(in srgb, var(--aid-acento) 20%, transparent), transparent 68%),
        radial-gradient(1200px 680px at 8% -12%,
                        color-mix(in srgb, var(--aid-acento) 14%, transparent), transparent 74%);
}

/* Contenido por encima de la capa de fondo. Header y drawer NO se tocan: Quasar los
   posiciona `fixed` y devolverlos al flujo descoloca la página entera. */
.nicegui-content, .q-page {
    position: relative; z-index: 1; background: transparent !important;
}

/* Superficies con datos: velo para que la marca de agua nunca compita con el texto. */
.aid-superficie {
    background: rgba(6, 6, 6, 0.80) !important;
    border: 1px solid var(--aid-borde) !important;
    backdrop-filter: blur(8px);
}
.aid-tabla {
    background: rgba(6, 6, 6, 0.88) !important;
    border: 1px solid var(--aid-borde) !important;
    backdrop-filter: blur(8px);
}
.aid-tabla thead tr th {
    position: sticky; top: 0; z-index: 2;
    background: #050505 !important; color: var(--aid-acento) !important; font-weight: 600;
    border-bottom: 1px solid var(--aid-borde) !important;
}
.aid-tabla td, .aid-tabla th { border-color: #262626 !important; }
.aid-separador {
    background: color-mix(in srgb, var(--aid-borde) 35%, transparent) !important;
}

/* Campos: velo propio; sin él se transparenta la figura DENTRO del área de escritura. */
.q-field--outlined .q-field__control { background: rgba(6, 6, 6, 0.80) !important; }
.q-field--outlined .q-field__control:before { border-color: var(--aid-borde) !important; }
*:focus-visible { outline: 2px solid var(--aid-foco) !important; outline-offset: 1px; }

/* Cromo: riel de acento en el header y elemento activo del menú. */
.q-header {
    border-bottom: 1px solid var(--aid-borde) !important;
    box-shadow: inset 0 3px 0 0 var(--aid-acento);
}
.q-drawer { border-right: 1px solid var(--aid-borde) !important; }
.aid-nav-activo {
    color: var(--aid-acento) !important;
    box-shadow: inset 3px 0 0 0 var(--aid-acento);
    background: color-mix(in srgb, var(--aid-acento) 14%, transparent) !important;
}
.aid-marca {
    filter: drop-shadow(0 0 10px color-mix(in srgb, var(--aid-acento) 60%, transparent));
}

/* Selector de tema. */
.aid-tema-menu {
    background: rgba(4, 4, 4, 0.97) !important;
    border: 1px solid var(--aid-borde); backdrop-filter: blur(12px);
}
.aid-tema-opcion { position: relative; cursor: pointer; border: 1px solid transparent; }
.aid-tema-opcion:hover { background: rgba(255,255,255,.08); border-color: var(--aid-borde); }
.aid-tema-elegido {
    border-color: var(--aid-acento) !important; background: rgba(255,255,255,.06);
}
.aid-tema-punto {
    position: absolute; top: 4px; right: 4px;
    width: 7px; height: 7px; border-radius: 50%;
}

/* Banda de tripulación: `ui.image` envuelve el <img> en un .q-img que se estira, así
   que el tamaño se fija en el WRAPPER, no en la imagen. */
.aid-banda .q-img {
    flex: 0 0 auto; width: 76px; height: 100px; min-height: 0;
    transition: transform .2s ease, filter .2s ease;
}
.aid-banda .q-img > img { object-fit: contain; object-position: bottom; }
.aid-banda .q-img:hover {
    transform: translateY(-6px) scale(1.06);
    filter: drop-shadow(0 0 12px color-mix(in srgb, var(--aid-acento) 70%, transparent));
}

/* Gráficos: mismo velo que tablas y tarjetas. Sin él, con la marca de agua a plena
   presencia, la figura se cuela por detrás de ejes y leyendas y no se leen. */
.aid-graf {
    position: relative;
    background: rgba(6, 6, 6, 0.86);
    border: 1px solid var(--aid-borde);
    border-radius: 0.75rem;
    padding: 0.25rem;
    backdrop-filter: blur(8px);
}
.aid-fsbtn { position: absolute; top: 4px; left: 4px; z-index: 5; }
</style>
""".replace("BORDE_", BORDE).replace("FOCO_", FOCO)

# Resize de los gráficos Plotly al entrar/salir de pantalla completa (un solo listener).
_FS = """
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


def instalar() -> None:
    """Arranque del sistema visual. Se llama UNA vez, desde `main.py`."""
    aplicar_defaults()
    # `shared=True` es lo que permite inyectar desde el ambito global con `ui.page`:
    # el CSS se anade a TODAS las paginas una sola vez, en lugar de reinyectarlo en
    # cada render (que era el antipatron anterior). Lo exige la propia NiceGUI.
    ui.add_head_html(_CSS, shared=True)
    ui.add_head_html(_FS, shared=True)


def aplicar_a_pagina(titulo: str) -> Tema:
    """Aplica el tema de la página con la API de Python (sin inyectar CSS por página)."""
    tema = tema_activo(titulo)
    ui.dark_mode(value=True)
    ui.colors(primary=tema.acento, secondary=BORDE, accent=FOCO,
              positive="#23D18B", negative="#F14C4C", warning=FOCO,
              dark=FONDO, dark_page=FONDO)
    # `ui.query('body')` es la vía sancionada por la guía para estilar la página, en
    # lugar de inyectar un <style> nuevo en cada render.
    ui.query("body").classes("bg-black text-white").style(variables(tema))
    return tema
