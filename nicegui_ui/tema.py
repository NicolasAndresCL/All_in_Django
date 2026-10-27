"""
tema.py — Sistema visual de la UI (personalización GLOBAL, no elemento por elemento).

Sigue la guía oficial de NiceGUI (`nicegui/llms.md`, "The Golden Rule – Python First"):
la personalización se hace de arriba abajo y el CSS crudo es el último recurso.

    1. `aplicar_defaults()`  — `default_props` / `default_classes` / `default_style` por
       tipo de elemento. Se llama UNA vez al arrancar y afecta a todo lo que se cree
       después, así que las vistas ya no repiten `.props('outlined dense')` por campo.
    2. `ui.query('body')`    — estilado a nivel de página (las variables del tema y el
       fondo: la cubierta de madera, `CUBIERTA`, o el cielo austral, `CIELO`). La guía
       marca `add_head_html('<style>body{...}</style>')` como ANTIPATRÓN para esto — y aquí
       además es lo ÚNICO que funciona: Quasar pinta `body.body--dark` con el shorthand
       `background`, que resetearía a none cualquier `background-image` de la hoja.
    3. Clases **Tailwind** en los elementos: es la herramienta primaria de estilo (y la
       de la responsividad: `grid-cols-1 md:grid-cols-2 2xl:grid-cols-3`…).
    4. `ui.add_head_html`    — SOLO para lo que la API de Python no puede expresar:
       pseudo-elementos `body::before/::after` (marca de agua, estrellas, cortinas de
       aurora), `@keyframes`, `:fullscreen`, `@media (hover: none)` y el estilo interno
       de Plotly (`.modebar-container`). Se inyecta UNA vez al arrancar.

Identidad visual, en dos ESTILOS que comparten estructura:

    - **Aurora austral** (`estilo="aurora"`, el tema POR DEFECTO desde la 2.2.0): cielo
      nocturno del sur de Chile con cortinas de aurora que se mueven despacio, estrellas,
      superficies de vidrio esmerilado y cifras en degradado. Sin ilustración de fondo:
      el contenido es el protagonista y en un móvil no compite con nada.
    - **Cubierta** (`estilo="cubierta"`): los 16 temas por personaje de siempre (marca de
      agua + aura + madera procedural), intactos y seleccionables.

    El tema elegido se guarda en `app.storage.user`, que es **por usuario/navegador**. NO
    se usa `app.storage.general`: ese ámbito es "todos los usuarios" y persiste en un
    archivo dentro del proyecto, así que el tema se filtraba a otras instancias.
    "Auto" sigue existiendo: el personaje propio de cada página (`IDENTIDAD`).
"""

from __future__ import annotations

from dataclasses import dataclass

from nicegui import app, ui

from nicegui_ui.plotly_tema import PLANTILLA

# ─── Paleta base: VS Code Dark High Contrast (estilo cubierta) ────────────────
FONDO = "#000000"        # editor.background (negro puro)
BORDE = "#6FC3DF"        # contrastBorder (cian)
FOCO = "#F38518"         # focusBorder (naranja)

# ─── Paleta del cielo austral (estilo aurora) ────────────────────────────────
NOCHE = "#050814"        # fondo: azul noche, no negro (el negro puro aplana el vidrio)
AURORA_VERDE = "#2EE6C9"  # acento: 11,8:1 sobre la superficie #0c1222
AURORA_VIOLETA = "#A78BFA"  # 6,9:1
AURORA_ROSA = "#F472B6"   # 7,1:1
# Texto SOBRE un relleno de acento (botones primarios). Blanco sobre cualquiera de los
# 17 acentos daba 1,3–3,4:1 (suspende AA); esta tinta oscura da 5,6–14:1 en todos.
TINTA_SOBRE_ACENTO = "#04121A"

# Prefijo con el que `main.py` publica nicegui_ui/static/fondos/.
FONDOS_URL = "/fondos"

# Emblema de la app en el drawer.
MARCA = f"{FONDOS_URL}/mugiwara.png"

# Plantilla Plotly propia (registrada en `plotly_tema.py`, que es puro y testeable).
PLOTLY_TEMPLATE = PLANTILLA

ESTILO_AURORA, ESTILO_CUBIERTA = "aurora", "cubierta"


@dataclass(frozen=True)
class Tema:
    """Un tema completo: figura de fondo (o ninguna), acento, opacidad y estilo.

    `opacidad` no es un número a ojo: `scripts/preparar_fondos.py` mide el brillo medio
    de los píxeles visibles de cada PNG y compensa. Las figuras oscuras (Brook de frac
    negro, Sanji, Zoro) necesitan mucha más opacidad que un emblema claro para leerse
    con la misma presencia; con un valor único unas quedan apagadas y otras deslumbran.
    El tema aurora no lleva figura (`archivo=None`, `opacidad=0`).
    """

    archivo: str | None
    acento: str
    etiqueta: str
    opacidad: float
    estilo: str = ESTILO_CUBIERTA


TEMA_AUTO = "auto"
TEMA_AURORA = "aurora"
TEMA_POR_DEFECTO = TEMA_AURORA

TEMAS: dict[str, Tema] = {
    TEMA_AURORA: Tema(None, AURORA_VERDE, "Aurora austral", 0.0, ESTILO_AURORA),
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

# Página → clave de TEMAS (modo "Auto"). Reparto semántico, no decorativo:
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


# ─── Fondos inline de body ───────────────────────────────────────────────────
# Van como estilo INLINE de body (vía `ui.query('body').style`), no en la hoja global, y
# el color de fondo se pinta AQUÍ en vez de con una clase `bg-*`: Quasar declara sus
# utilidades de color como `background: #000 !important`, y ese shorthand con !important
# resetea `background-image` a none — con la clase puesta, el fondo se define pero no se
# dibuja (comprobado en el navegador).

# La cubierta del barco: madera PROCEDURAL (gradientes apilados), 0 KB, teñida con el
# acento del personaje. Todo a opacidades bajas: la insinuación de unos tablones.
CUBIERTA = (
    f"background-color: {FONDO};"
    "background-image:"
    # Tinte del personaje sobre la cubierta.
    " linear-gradient(180deg, color-mix(in srgb, var(--aid-acento) 7%, transparent),"
    " transparent 62%),"
    # Vetas: rayas finas e irregulares a lo largo del tablón.
    " repeating-linear-gradient(90deg,"
    " rgba(168,108,54,.07) 0 3px, transparent 3px 11px,"
    " rgba(120,74,35,.06) 11px 13px, transparent 13px 29px,"
    " rgba(168,108,54,.05) 29px 31px, transparent 31px 53px),"
    # Juntas: calafateado oscuro + el canto iluminado del tablón siguiente.
    " repeating-linear-gradient(0deg,"
    " rgba(104,64,30,.22) 0 74px,"
    " rgba(146,92,46,.16) 74px 76px,"
    " rgba(0,0,0,.62) 76px 80px),"
    # Luz de cubierta: entra por proa y se apaga hacia los costados.
    " radial-gradient(120% 80% at 50% 0%, rgba(150,96,48,.16), transparent 72%);"
    # Fija: el contenido navega sobre la cubierta, la cubierta no scrollea.
    "background-attachment: fixed;"
)

# El cielo austral: la base estática sobre la que se mueven las cortinas (`body::after`)
# y titilan las estrellas (`body::before`). Tres capas: el resplandor del horizonte
# polar arriba, un eco violeta abajo a la derecha y el degradado de la noche.
CIELO = (
    f"background-color: {NOCHE};"
    "background-image:"
    " radial-gradient(120% 70% at 50% -12%, rgba(30, 58, 110, .55), transparent 70%),"
    " radial-gradient(80% 60% at 100% 100%, rgba(76, 29, 149, .20), transparent 70%),"
    f" linear-gradient(180deg, #070B1C 0%, {NOCHE} 55%, #04060F 100%);"
    "background-attachment: fixed;"
)


# ─── Resolución del tema ─────────────────────────────────────────────────────
def url_fondo(tema: Tema) -> str:
    return f"{FONDOS_URL}/{tema.archivo}" if tema.archivo else "none"


def es_aurora(tema: Tema) -> bool:
    return tema.estilo == ESTILO_AURORA


def tema_de_pagina(titulo: str) -> Tema:
    return TEMAS[IDENTIDAD.get(titulo, IDENTIDAD_POR_DEFECTO)]


def tema_elegido() -> str:
    """Clave del tema fijado por ESTE usuario; sin elección, el tema por defecto.

    `app.storage.user` exige `storage_secret` y un contexto de petición; fuera de él
    (tests unitarios, importación) no hay usuario y la respuesta es el por defecto.
    """
    try:
        return app.storage.user.get("tema", TEMA_POR_DEFECTO)
    except (RuntimeError, AttributeError):
        return TEMA_POR_DEFECTO


def fijar_tema(clave: str) -> None:
    app.storage.user["tema"] = clave


def tema_activo(titulo: str, clave: str | None = None) -> Tema:
    """El tema que se aplica: el elegido (o `clave`) si existe; en Auto, el de la página."""
    clave = tema_elegido() if clave is None else clave
    return TEMAS[clave] if clave in TEMAS else tema_de_pagina(titulo)


def variables(tema: Tema) -> str:
    """Estilo inline de body: custom properties del tema + su fondo.

    Definirlas sobre `body` —y no en un `<style>` inyectado por página— es lo que
    permite cambiar de tema sin acumular bloques de CSS en el head.
    """
    fondo = "none" if not tema.archivo else f"url('{url_fondo(tema)}')"
    return (f"--aid-acento: {tema.acento};"
            f"--aid-fondo: {fondo};"
            f"--aid-opacidad: {tema.opacidad};"
            + (CIELO if es_aurora(tema) else CUBIERTA))


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
    # Toda imagen rebota: el efecto se declara una vez aquí en vez de repetir la clase
    # en cada `ui.image` de las vistas (y en las que se añadan mañana).
    ui.image.default_props("no-spinner fit=contain")
    ui.image.default_classes("aid-rebote")
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
    /* El personaje va sobre cubierta: se mece con el barco. Muy lento y de recorrido
       corto — un vaivén perceptible aquí, a 84vh de alto, marearía. */
    animation: aid-mecer 11s ease-in-out infinite;
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
/* NiceGUI da 16 px de padding a `.nicegui-content`, que se SUMABAN al del shell: a 360 px
   se perdían 56 px de ancho entre ambos. Manda solo el del shell (`p-3 sm:p-4 lg:p-6`). */
.nicegui-content { padding: 0; }
/* Los paneles de pestañas (`ui.tab_panels`) traen fondo opaco de Quasar (`q-dark`):
   tapaban el cielo/cubierta con un rectángulo negro. Lo que lleva datos ya tiene velo. */
.q-tab-panels { background: transparent !important; }

/* ─── Movimiento: rebote de las imágenes ─────────────────────────────────────
   Se aplica a TODA `ui.image` desde `aplicar_defaults()`, así que la clase cuelga del
   wrapper `.q-img` y no del <img>: animar el wrapper evita pelearse con el `object-fit`
   interno de Quasar. Los delays NEGATIVOS por posición arrancan cada figura en un punto
   distinto del ciclo; sin ellos, doce personajes saltando al unísono parecen un fallo
   de render y no una tripulación. */
@keyframes aid-rebote {
    0%, 100% { transform: translateY(0) scale(1); }
    22%      { transform: translateY(-9px) scale(1.015); }
    45%      { transform: translateY(0) scale(.985); }
    62%      { transform: translateY(-4px) scale(1.004); }
    80%      { transform: translateY(0) scale(1); }
}
@keyframes aid-mecer {
    0%, 100% { transform: translateY(0) rotate(0deg); }
    50%      { transform: translateY(-1.2vh) rotate(.55deg); }
}
.aid-rebote {
    animation: aid-rebote 3.4s cubic-bezier(.34, .72, .4, 1) infinite;
    will-change: transform;
}
.aid-rebote:nth-child(2n)   { animation-delay: -.55s; }
.aid-rebote:nth-child(3n)   { animation-delay: -1.20s; }
.aid-rebote:nth-child(4n+1) { animation-delay: -1.85s; }
.aid-rebote:nth-child(5n+2) { animation-delay: -2.40s; }
/* Con el ratón encima manda el hover. Hay que APAGAR la animación, no pausarla: el
   transform de una animación en curso gana a cualquier regla del hover. */
.aid-rebote:hover { animation: none; }

/* Superficies con datos: velo para que la marca de agua nunca compita con el texto,
   teñido con el acento para que la tarjeta también lleve el color del personaje. El
   degradado muere en negro antes de la mitad, así que el texto conserva su contraste. */
.aid-superficie {
    background: linear-gradient(157deg,
                    color-mix(in srgb, var(--aid-acento) 13%, rgba(6, 6, 6, .86)) 0%,
                    rgba(6, 6, 6, .86) 48%) !important;
    border: 1px solid color-mix(in srgb, var(--aid-acento) 45%, transparent) !important;
    box-shadow: inset 0 1px 0 0 color-mix(in srgb, var(--aid-acento) 30%, transparent),
                0 8px 26px rgba(0, 0, 0, .45);
    backdrop-filter: blur(8px);
    transition: border-color .18s ease, box-shadow .18s ease;
}
.aid-superficie:hover {
    border-color: var(--aid-acento) !important;
    box-shadow: inset 0 1px 0 0 color-mix(in srgb, var(--aid-acento) 55%, transparent),
                0 0 22px -6px color-mix(in srgb, var(--aid-acento) 65%, transparent),
                0 10px 30px rgba(0, 0, 0, .5);
}
.aid-tabla {
    background: rgba(6, 6, 6, 0.88) !important;
    border: 1px solid color-mix(in srgb, var(--aid-acento) 45%, var(--aid-borde)) !important;
    backdrop-filter: blur(8px);
}
.aid-tabla thead tr th {
    position: sticky; top: 0; z-index: 2;
    background: #050505 !important; color: var(--aid-acento) !important; font-weight: 600;
    border-bottom: 1px solid var(--aid-acento) !important;
}
.aid-tabla td, .aid-tabla th { border-color: #262626 !important; }
.aid-separador {
    background: color-mix(in srgb, var(--aid-acento) 45%, transparent) !important;
}

/* Campos: velo propio; sin él se transparenta la figura DENTRO del área de escritura. */
.q-field--outlined .q-field__control { background: rgba(6, 6, 6, 0.80) !important; }
.q-field--outlined .q-field__control:before { border-color: var(--aid-borde) !important; }
*:focus-visible { outline: 2px solid var(--aid-foco) !important; outline-offset: 1px; }
/* Cabecera del `ui.upload`: Quasar la pinta con el acento y texto blanco (1,6:1 sobre el
   verde aurora). Sin `!important`: la regla de Quasar es normal y la hoja sin capa gana. */
.q-uploader__header { color: TINTA_ACENTO_; }

/* ─── Cromo: header y drawer llevan el color del personaje ───────────────────
   El degradado arranca en el acento y se apaga a negro antes de la mitad: identifica
   la sección de un vistazo sin restarle contraste al texto blanco de encima. Las
   clases son propias (`aid-header`/`aid-drawer`) en vez de `.q-header`/`.q-drawer`
   porque las pone `layout.shell()`; el posicionamiento `fixed` de Quasar se respeta. */
.aid-header {
    background: linear-gradient(115deg,
                    color-mix(in srgb, var(--aid-acento) 38%, #050505) 0%,
                    color-mix(in srgb, var(--aid-acento) 12%, #050505) 34%,
                    #050505 68%) !important;
    border-bottom: 1px solid color-mix(in srgb, var(--aid-acento) 65%, transparent) !important;
    box-shadow: inset 0 3px 0 0 var(--aid-acento), 0 6px 24px rgba(0, 0, 0, .55);
}
.aid-drawer {
    background: linear-gradient(180deg,
                    color-mix(in srgb, var(--aid-acento) 30%, #050505) 0%,
                    color-mix(in srgb, var(--aid-acento) 9%, #050505) 26%,
                    #050505 55%) !important;
    border-right: 1px solid color-mix(in srgb, var(--aid-acento) 55%, transparent) !important;
}
.aid-nav-activo {
    color: var(--aid-acento) !important;
    box-shadow: inset 3px 0 0 0 var(--aid-acento);
    background: color-mix(in srgb, var(--aid-acento) 18%, transparent) !important;
}
.aid-marca {
    filter: drop-shadow(0 0 10px color-mix(in srgb, var(--aid-acento) 60%, transparent));
}
/* Cifra de una métrica: el acento como TINTA (clase propia, no `text-primary`: ver la
   trampa de capas en `_CSS_CAPA_TEMA`). */
.aid-cifra { color: var(--aid-acento); font-variant-numeric: normal; }

/* Selector de tema. */
.aid-tema-menu {
    background: rgba(4, 4, 4, 0.97) !important;
    border: 1px solid var(--aid-acento); backdrop-filter: blur(12px);
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
/* Muestra del tema aurora en el selector (no tiene figura: es un trozo de cielo). */
.aid-muestra-aurora {
    border-radius: 9999px;
    background: conic-gradient(from 210deg, AV_, AVI_, AR_, AV_);
    box-shadow: 0 0 14px -2px AV_;
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

/* ─── Gráficos ───────────────────────────────────────────────────────────────
   La tarjeta (`aid-graf` + `aid-superficie`) es la superficie; el lienzo de Plotly es
   transparente. La ALTURA depende del ancho (clamp sobre vw): con px fijos, en un móvil
   quedaban tiras altas y flacas, y en escritorio sobraba aire. Plotly ocupa la altura
   del contenedor porque las figuras no fijan `height` (autosize). */
.aid-graf { position: relative; min-width: 0; }
.aid-lienzo { width: 100%; min-width: 0; }
.aid-alto-s  { height: clamp(220px, 56vw, 300px); }
.aid-alto-m  { height: clamp(260px, 70vw, 360px); }
.aid-alto-l  { height: clamp(340px, 96vw, 480px); }
.aid-alto-xl { height: clamp(460px, 150vw, 680px); }
.aid-fsbtn { opacity: .75; transition: opacity .15s ease; }
.aid-fsbtn:hover, .aid-fsbtn:focus-visible { opacity: 1; }

/* Barra de herramientas de Plotly: solo con puntero fino y pantalla ancha. En táctil
   (sin hover) o a menos de 640 px, una barra de iconos encima de un gráfico chico tapa
   más de lo que aporta; vuelve en pantalla completa, donde sí hay sitio. */
.aid-graf .modebar-container { top: 2px !important; }
@media (hover: none), (max-width: 639px) {
    .aid-graf:not(:fullscreen):not(.aid-graf--max) .modebar-container { display: none !important; }
}

/* Pantalla completa: Fullscreen API donde existe (escritorio, Android, iPadOS) y, donde
   no (iPhone: Safari solo la permite en <video>), una capa fija que ocupa la ventana. */
.aid-graf:fullscreen, .aid-graf.aid-graf--max {
    background: NOCHE_ !important; padding: 1rem !important; border-radius: 0 !important;
}
.aid-graf.aid-graf--max { position: fixed !important; inset: 0; z-index: 6000; margin: 0; }
.aid-graf:fullscreen .aid-lienzo, .aid-graf.aid-graf--max .aid-lienzo {
    height: calc(100dvh - 5rem) !important;
}

/* ════════════════════ ESTILO AURORA AUSTRAL (por defecto) ════════════════════
   Todo cuelga de `body.aid-aurora`: más específico que las reglas del estilo
   cubierta, así que las reemplaza sin tocarlas. */

/* Estrellas: un patrón de puntos de 1-2 px que se repite cada 340 px y se apaga hacia
   abajo (más cielo arriba, más "tierra" abajo). Sustituye a la marca de agua. */
body.aid-aurora::before {
    background-image:
        radial-gradient(1.2px 1.2px at 12% 18%, rgba(255,255,255,.85), transparent 60%),
        radial-gradient(1px 1px at 33% 62%, rgba(255,255,255,.55), transparent 60%),
        radial-gradient(1.5px 1.5px at 58% 28%, rgba(220,230,255,.80), transparent 60%),
        radial-gradient(1px 1px at 76% 74%, rgba(255,255,255,.45), transparent 60%),
        radial-gradient(1.3px 1.3px at 91% 12%, rgba(200,255,245,.75), transparent 60%),
        radial-gradient(1px 1px at 47% 88%, rgba(255,255,255,.40), transparent 60%),
        radial-gradient(1px 1px at 5% 80%, rgba(255,255,255,.50), transparent 60%);
    background-size: 340px 340px; background-repeat: repeat; background-position: 0 0;
    opacity: .7; filter: none;
    -webkit-mask-image: linear-gradient(180deg, #000 0%, rgba(0,0,0,.6) 45%, transparent 85%);
    mask-image: linear-gradient(180deg, #000 0%, rgba(0,0,0,.6) 45%, transparent 85%);
    animation: aid-titilar 6s ease-in-out infinite alternate;
}
/* Las cortinas: tres elipses de color, difuminadas y deformadas lentamente. Se anima
   `transform` (compositor, sin repintar) sobre una capa ya difuminada: barato también
   en un móvil. */
body.aid-aurora::after {
    inset: -18% -12% auto -12%; height: 78vh;
    background:
        radial-gradient(38% 58% at 18% 34%, rgba(46, 230, 201, .30), transparent 70%),
        radial-gradient(34% 54% at 52% 22%, rgba(167, 139, 250, .26), transparent 70%),
        radial-gradient(30% 48% at 84% 36%, rgba(244, 114, 182, .18), transparent 70%);
    filter: blur(46px) saturate(1.25);
    transform-origin: 50% 0;
    animation: aid-aurora 28s ease-in-out infinite alternate;
}
@keyframes aid-aurora {
    0%   { transform: translate3d(-3%, 0, 0) skewX(-8deg) scaleY(1); }
    50%  { transform: translate3d(2%, 3%, 0) skewX(4deg) scaleY(1.14); }
    100% { transform: translate3d(4%, -1%, 0) skewX(9deg) scaleY(.94); }
}
@keyframes aid-titilar { from { opacity: .45; } to { opacity: .8; } }

/* Vidrio: velo azul noche casi opaco (el texto conserva >= 15:1) con un reflejo
   verde-violeta en la esquina y un filo de luz arriba.
   SIN `backdrop-filter` a propósito: con el cielo ANIMADO detrás, el navegador tiene que
   re-desenfocar el fondo de cada tarjeta en cada fotograma. Con ~20 tarjetas una captura
   de página completa a 360 px no terminaba en 30 s; en un móvil sería batería y tirones.
   Con un velo al 84 % el desenfoque casi no se ve: se queda solo en header y drawer. */
body.aid-aurora .aid-superficie {
    background:
        linear-gradient(160deg, rgba(46, 230, 201, .08), rgba(167, 139, 250, .05) 38%,
                        rgba(255, 255, 255, 0) 68%),
        rgba(11, 16, 34, .84) !important;
    border: 1px solid rgba(148, 163, 184, .16) !important;
    box-shadow: inset 0 1px 0 0 rgba(255, 255, 255, .07), 0 14px 34px -14px rgba(0, 0, 0, .65);
    backdrop-filter: none;
}
body.aid-aurora .aid-superficie:hover {
    border-color: rgba(46, 230, 201, .45) !important;
    box-shadow: inset 0 1px 0 0 rgba(255, 255, 255, .10),
                0 0 0 1px rgba(46, 230, 201, .12),
                0 18px 42px -16px rgba(46, 230, 201, .38);
}
body.aid-aurora .aid-tabla {
    background: rgba(11, 16, 34, .88) !important;
    border: 1px solid rgba(148, 163, 184, .16) !important;
    backdrop-filter: none;
}
body.aid-aurora .aid-tabla thead tr th {
    background: #0B1022 !important; border-bottom: 1px solid rgba(46, 230, 201, .55) !important;
}
body.aid-aurora .aid-tabla td, body.aid-aurora .aid-tabla th {
    border-color: rgba(148, 163, 184, .10) !important;
}
body.aid-aurora .aid-separador {
    background: linear-gradient(90deg, transparent, rgba(46, 230, 201, .45),
                                rgba(167, 139, 250, .45), transparent) !important;
}
body.aid-aurora .q-field--outlined .q-field__control {
    background: rgba(11, 16, 34, .72) !important; border-radius: .6rem;
}
body.aid-aurora .q-field--outlined .q-field__control:before {
    border-color: rgba(148, 163, 184, .32) !important; border-radius: .6rem;
}
body.aid-aurora *:focus-visible { outline-color: AV_ !important; }

/* Cromo de vidrio con la aurora como filo: una línea de 2 px verde → violeta → rosa. */
body.aid-aurora .aid-header {
    background:
        linear-gradient(90deg, AV_, AVI_ 50%, AR_) bottom / 100% 2px no-repeat,
        rgba(6, 9, 22, .74) !important;
    border-bottom: 0 !important;
    box-shadow: 0 10px 30px -12px rgba(0, 0, 0, .7);
    backdrop-filter: blur(14px) saturate(1.4);
}
body.aid-aurora .aid-drawer {
    background: linear-gradient(180deg, rgba(46, 230, 201, .10), transparent 32%),
                rgba(6, 9, 22, .90) !important;
    border-right: 1px solid rgba(148, 163, 184, .14) !important;
    backdrop-filter: blur(16px);
}
body.aid-aurora .aid-nav-activo {
    background: linear-gradient(90deg, rgba(46, 230, 201, .20), rgba(167, 139, 250, .06) 70%,
                                transparent) !important;
}
body.aid-aurora .aid-tema-menu {
    background: rgba(8, 12, 28, .96) !important; border-color: rgba(148, 163, 184, .25);
}
/* Cifras en degradado de aurora. Los dos extremos superan 4,5:1 sobre la superficie
   (11,8:1 y 6,9:1), así que el texto es AA en cualquier punto del degradado. */
body.aid-aurora .aid-cifra {
    background: linear-gradient(92deg, AV_, AVI_);
    -webkit-background-clip: text; background-clip: text; color: transparent;
}
@media (forced-colors: active) {
    body.aid-aurora .aid-cifra { background: none; color: CanvasText; }
}

/* Quien pide menos movimiento se queda con el mismo diseño, quieto. */
@media (prefers-reduced-motion: reduce) {
    .aid-rebote, body::before, body::after, body.aid-aurora::before,
    body.aid-aurora::after { animation: none !important; }
}
</style>
""".replace("BORDE_", BORDE).replace("FOCO_", FOCO).replace("NOCHE_", NOCHE) \
   .replace("TINTA_ACENTO_", TINTA_SOBRE_ACENTO) \
   .replace("AVI_", AURORA_VIOLETA).replace("AV_", AURORA_VERDE).replace("AR_", AURORA_ROSA)

# TRAMPA DE CAPAS. NiceGUI 3 declara `@layer theme, base, quasar, nicegui, components,
# utilities, overrides, quasar_importants`. Con declaraciones `!important` el orden de
# las capas se INVIERTE: gana la capa declarada ANTES, y el CSS sin capa (el de `_CSS`)
# es el MÁS DÉBIL. Por eso un `color: ... !important` sin capa pierde contra el
# `.text-white { color: #fff !important }` de Quasar (capa `quasar_importants`). Para
# vencerlo hay que declarar el `!important` en la PRIMERA capa (`theme`).
# Lo único que lo necesita: la tinta oscura de los botones primarios (AA, ver arriba).
_CSS_CAPA_TEMA = f"""
<style>
@layer theme {{
    .q-btn.bg-primary.text-white {{ color: {TINTA_SOBRE_ACENTO} !important; }}
}}
</style>
"""

# Pantalla completa de un gráfico (un solo manejador global, sin ida y vuelta al
# servidor: el botón lo invoca con `js_handler`). Fullscreen API con prefijo webkit
# (iPadOS) y, si no existe o la rechaza (iPhone), la capa `.aid-graf--max`. El resize de
# Plotly lo hace el ResizeObserver del propio componente de NiceGUI al cambiar el tamaño.
_JS = """
<script>
(() => {
  if (window.aidPantallaCompleta) return;
  const maximizar = (el, si) => {
    el.classList.toggle('aid-graf--max', si);
    document.body.style.overflow = si ? 'hidden' : '';
  };
  window.aidPantallaCompleta = (el) => {
    if (!el) return;
    const d = document;
    if (d.fullscreenElement || d.webkitFullscreenElement) {
      (d.exitFullscreen || d.webkitExitFullscreen).call(d);
      return;
    }
    if (el.classList.contains('aid-graf--max')) { maximizar(el, false); return; }
    const pedir = el.requestFullscreen || el.webkitRequestFullscreen;
    if (!pedir) { maximizar(el, true); return; }
    try {
      Promise.resolve(pedir.call(el)).catch(() => maximizar(el, true));
    } catch (e) { maximizar(el, true); }
  };
  document.addEventListener('keydown', (ev) => {
    if (ev.key !== 'Escape') return;
    document.querySelectorAll('.aid-graf--max').forEach((el) => maximizar(el, false));
  });
})();
</script>
"""


def instalar() -> None:
    """Arranque del sistema visual. Se llama UNA vez, desde `main.py`."""
    aplicar_defaults()
    # `shared=True` es lo que permite inyectar desde el ambito global con `ui.page`:
    # el CSS se anade a TODAS las paginas una sola vez, en lugar de reinyectarlo en
    # cada render (que era el antipatron anterior). Lo exige la propia NiceGUI.
    ui.add_head_html(_CSS, shared=True)
    ui.add_head_html(_CSS_CAPA_TEMA, shared=True)
    ui.add_head_html(_JS, shared=True)


def aplicar_a_pagina(titulo: str) -> Tema:
    """Aplica el tema de la página con la API de Python (sin inyectar CSS por página)."""
    tema = tema_activo(titulo)
    aurora = es_aurora(tema)
    fondo = NOCHE if aurora else FONDO
    ui.dark_mode(value=True)
    ui.colors(primary=tema.acento, secondary=AURORA_VIOLETA if aurora else BORDE,
              accent=FOCO, positive="#23D18B", negative="#F14C4C", warning=FOCO,
              dark=fondo, dark_page=fondo)
    # `ui.query('body')` es la vía sancionada por la guía para estilar la página, en
    # lugar de inyectar un <style> nuevo en cada render.
    # Sin `bg-black`: esa utilidad de Quasar lleva `!important` y borraría el fondo
    # (el color lo pinta `CUBIERTA`/`CIELO` con `background-color`).
    cuerpo = ui.query("body").classes("text-white").style(variables(tema))
    if aurora:
        cuerpo.classes("aid-aurora")
    return tema
