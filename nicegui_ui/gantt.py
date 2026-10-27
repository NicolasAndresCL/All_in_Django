"""
gantt.py — Gráficos Gantt de horarios (Plotly), para la UI.

Portado de `all_in_one/core/horarios_logic.py`. Funciones puras que reciben listas
de dicts tal como las devuelve la API (entrada/salida como 'HH:MM:SS' o None) y
devuelven `plotly.graph_objects.Figure`. Se dibujan con `layout.grafico`.

**Eje de tiempo REAL (tipo `date`), no numérico con 20 `tickvals` fijos.** Con ticks
fijos, por debajo de ~420 px las etiquetas de hora se apilaban ilegibles; con un eje de
fecha Plotly elige solo el paso (1 h, 2 h, 3 h, 6 h…) según el ancho disponible. Las
horas se anclan a un día ficticio (`_DIA_0`) y la madrugada cae en `_DIA_0 + 1`, que
es exactamente lo que ya hacía `hora_a_decimal` (01:00 → 25.0). Es la misma técnica
que `px.timeline`: `base` = instante de inicio, `x` = duración en milisegundos.

Sin `height` ni título dentro de la figura: la altura la pone el contenedor por CSS
según el ancho, y el título va en la cabecera de la tarjeta (`layout.grafico`).
"""

from __future__ import annotations

from datetime import datetime, timedelta

import plotly.graph_objects as go

from nicegui_ui.plotly_tema import PALETA, PLANTILLA

DIAS_ORDEN = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
DIAS_CORTOS = dict(zip(DIAS_ORDEN, ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"], strict=True))
TRABAJADORES = ["Manu", "Jorge", "Babi", "Nico"]
# Color por ENTIDAD (cada persona conserva el suyo aunque un filtro oculte a otras):
# los cuatro primeros slots de la paleta validada, en su orden.
COLORES_TRABAJADOR = dict(zip(TRABAJADORES, PALETA[:4], strict=True))
COLOR_ESTUDIO, COLOR_TRABAJO = PALETA[0], PALETA[1]

_DIA_0 = datetime(2000, 1, 3)  # un lunes cualquiera: solo importa la hora
_MS_HORA = 3_600_000


def hora_a_decimal(valor):
    """'HH:MM[:SS]' → decimal. Horas < 8 se consideran del día siguiente (01:00 → 25.0)."""
    if not valor or valor in ("LIBRE", "None"):
        return None
    partes = str(valor).split(":")
    hh, mm = int(partes[0]), int(partes[1]) if len(partes) > 1 else 0
    dec = hh + mm / 60
    if hh < 8:
        dec += 24
    return dec


def instante(decimal: float) -> str:
    """Hora decimal (puede pasar de 24) → ISO sobre el día ficticio, para el eje `date`."""
    return (_DIA_0 + timedelta(hours=decimal)).isoformat()


def _hm(valor) -> str:
    return str(valor)[:5] if valor else ""


def _intervalo(entrada, salida) -> tuple[float, float] | None:
    ini, fin = hora_a_decimal(entrada), hora_a_decimal(salida)
    if ini is None or fin is None:
        return None
    if fin <= ini:
        fin += 24
    return ini, fin


def _eje_horas(desde: float, hasta: float) -> dict:
    return dict(type="date", range=[instante(desde), instante(hasta)], tickformat="%H:%M",
                title=None, showgrid=True, hoverformat="%H:%M")


def _eje_dias() -> dict:
    """Los 7 días SIEMPRE: con solo `categoryarray`, Plotly omite los días sin bloques
    (una semana sin turnos el finde perdía Sáb y Dom). `range` fija las 7 filas."""
    return dict(categoryorder="array", categoryarray=[DIAS_CORTOS[d] for d in reversed(DIAS_ORDEN)],
                range=[-0.5, 6.5], title=None, showgrid=False)


def _anclar_dias(fig: go.Figure, desde: float) -> None:
    """Traza invisible con los 7 días: así las 7 filas existen aunque alguna no tenga
    bloques (una semana sin turnos el finde perdía Sáb y Dom del eje)."""
    fig.add_trace(go.Bar(y=[DIAS_CORTOS[d] for d in DIAS_ORDEN], x=[0] * 7, base=[instante(desde)] * 7,
                         orientation="h", showlegend=False, hoverinfo="skip", marker_color="rgba(0,0,0,0)",
                         name="_dias"))


def generar_gantt(clases: list[dict], turnos: list[dict], semana_label: str = "") -> go.Figure:
    """Gantt personal: bloques de estudio y de trabajo superpuestos por día.

    Una traza por CATEGORÍA (no una por bloque): la leyenda sale sola, sin las trazas
    fantasma que había antes, y el color sigue a la categoría.
    """
    series = {
        "Santo Tomás": {"color": COLOR_ESTUDIO, "x": [], "base": [], "y": [], "text": [], "hover": []},
        "PedidosYa": {"color": COLOR_TRABAJO, "x": [], "base": [], "y": [], "text": [], "hover": []},
    }

    def _anadir(nombre: str, r: dict, texto: str, detalle: str) -> None:
        tramo = _intervalo(r.get("entrada"), r.get("salida"))
        if tramo is None:
            return
        ini, fin = tramo
        s = series[nombre]
        s["x"].append((fin - ini) * _MS_HORA)
        s["base"].append(instante(ini))
        s["y"].append(DIAS_CORTOS.get(r["dia"], r["dia"]))
        s["text"].append(texto)
        s["hover"].append(f"<b>{nombre}</b> · {r['dia']}<br>"
                          f"{_hm(r.get('entrada'))} – {_hm(r.get('salida'))}<br>{detalle}")

    for r in clases:
        _anadir("Santo Tomás", r, r.get("asignatura", ""),
                f"{r.get('asignatura', '')} · {r.get('horas', '')} h")
    for r in turnos:
        if not r.get("es_libre"):
            _anadir("PedidosYa", r, "PeYa", f"Neto: {r.get('neto', '')} h")

    fig = go.Figure()
    _anclar_dias(fig, 8)
    for nombre, s in series.items():
        fig.add_trace(go.Bar(
            name=nombre, x=s["x"], base=s["base"], y=s["y"], orientation="h",
            marker_color=s["color"], text=s["text"], textposition="inside",
            insidetextanchor="middle", textfont=dict(color="#ffffff", size=11),
            customdata=s["hover"], hovertemplate="%{customdata}<extra></extra>",
            # Leyenda presente aunque una categoría no tenga bloques esta semana.
            showlegend=True,
        ))
    fig.update_layout(template=PLANTILLA, barmode="overlay", bargap=0.35,
                      xaxis=_eje_horas(8, 28), yaxis=_eje_dias(),
                      meta={"semana": semana_label})
    # Mediodía como referencia (línea sólida y tenue: la rejilla no va punteada).
    fig.add_vline(x=instante(12), line_color="rgba(148,163,184,0.35)", line_width=1)
    return fig


def generar_gantt_equipo(turnos: list[dict]) -> go.Figure:
    """Gantt de equipo: 4 trabajadores agrupados por día.

    `turnos` con trabajador/dia/entrada/salida/neto/extra/es_libre.
    """
    X_MIN, X_MAX = 9.0, 27.0
    dias = list(reversed(DIAS_ORDEN))
    por_trab: dict = {}
    for r in turnos:
        por_trab.setdefault(r.get("trabajador"), {})[r.get("dia")] = r

    fig = go.Figure()
    _anclar_dias(fig, X_MIN)
    for trabajador in TRABAJADORES:
        dias_trab = por_trab.get(trabajador)
        if not dias_trab:
            continue
        anchos, bases, hovers = [], [], []
        for dia in dias:
            row = dias_trab.get(dia)
            tramo = None if not row or row.get("es_libre") else _intervalo(row.get("entrada"), row.get("salida"))
            if tramo is None:
                anchos.append(0)
                bases.append(instante(X_MIN))
                hovers.append(f"<b>{trabajador}</b> · {dia}<br>Libre")
                continue
            ini, fin = max(tramo[0], X_MIN), min(tramo[1], X_MAX)
            anchos.append(max(fin - ini, 0))
            bases.append(instante(ini))
            hovers.append(
                f"<b>{trabajador}</b> · {dia}<br>{_hm(row.get('entrada'))} – {_hm(row.get('salida'))}"
                f"<br>Neto: {row.get('neto', 0)} h · Extras: {row.get('extra', 0)} h"
            )
        fig.add_trace(go.Bar(
            name=trabajador, y=[DIAS_CORTOS[d] for d in dias], x=[a * _MS_HORA for a in anchos],
            base=bases, orientation="h", marker_color=COLORES_TRABAJADOR[trabajador],
            # `uniformtext` (plantilla) oculta el texto que no cabe en vez de encogerlo
            # hasta hacerlo ilegible: en móvil manda el tooltip.
            text=[f"{a:.1f} h" if a > 0 else "" for a in anchos], textposition="inside",
            insidetextanchor="middle", textfont=dict(color="#ffffff", size=11),
            hovertemplate="%{customdata}<extra></extra>", customdata=hovers,
            offsetgroup=trabajador,
        ))

    # En `barmode="group"` cada traza ocupa un hueco: el ancla de días comparte el de la
    # primera persona para no robarle ancho a las cuatro barras del día.
    if len(fig.data) > 1:
        fig.data[0].offsetgroup = fig.data[1].name
    fig.update_layout(template=PLANTILLA, barmode="group", bargap=0.22, bargroupgap=0.08,
                      xaxis=_eje_horas(X_MIN, X_MAX), yaxis=_eje_dias())
    return fig
