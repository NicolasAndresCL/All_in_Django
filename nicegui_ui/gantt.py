"""
gantt.py — Gráficos Gantt de horarios (Plotly), para la UI.

Portado de `all_in_one/core/horarios_logic.py`. Funciones puras que reciben listas
de dicts tal como las devuelve la API (entrada/salida como 'HH:MM:SS' o None) y
devuelven `plotly.graph_objects.Figure`. Se dibujan con `ui.plotly`.
"""

import plotly.graph_objects as go

DIAS_ORDEN = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
TRABAJADORES = ["Manu", "Jorge", "Babi", "Nico"]
COLORES_TRABAJADOR = {"Manu": "#378ADD", "Jorge": "#1D9E75", "Babi": "#D4537E", "Nico": "#17A1BA"}


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


def _hm(valor) -> str:
    return str(valor)[:5] if valor else ""


def generar_gantt(clases: list[dict], turnos: list[dict], semana_label: str) -> go.Figure:
    """Gantt personal: bloques de estudio (verde) y trabajo (rojo) superpuestos."""
    fig = go.Figure()

    for r in clases:
        ini, fin = hora_a_decimal(r.get("entrada")), hora_a_decimal(r.get("salida"))
        if ini is None or fin is None:
            continue
        if fin <= ini:
            fin += 24
        fig.add_trace(go.Bar(
            x=[fin - ini], y=[r["dia"]], base=[ini], orientation="h",
            marker_color="rgba(34, 139, 34, 0.82)",
            marker_line=dict(color="rgba(0,100,0,1)", width=1.5),
            hovertemplate=(
                f"<b>Santo Tomás</b><br>Asignatura: {r.get('asignatura', '')}<br>"
                f"Día: {r['dia']}<br>Horario: {_hm(r.get('entrada'))} – {_hm(r.get('salida'))}<br>"
                f"Duración: {r.get('horas', '')}h<extra></extra>"
            ),
            showlegend=False, text=r.get("asignatura", ""), textposition="inside",
            insidetextanchor="middle", textfont=dict(size=10, color="white"),
        ))

    for r in turnos:
        if r.get("es_libre"):
            continue
        ini, fin = hora_a_decimal(r.get("entrada")), hora_a_decimal(r.get("salida"))
        if ini is None or fin is None:
            continue
        if fin <= ini:
            fin += 24
        fig.add_trace(go.Bar(
            x=[fin - ini], y=[r["dia"]], base=[ini], orientation="h",
            marker_color="rgba(200, 30, 30, 0.82)",
            marker_line=dict(color="rgba(140,0,0,1)", width=1.5),
            hovertemplate=(
                f"<b>PedidosYa</b><br>Día: {r['dia']}<br>"
                f"Turno: {_hm(r.get('entrada'))} – {_hm(r.get('salida'))}<br>"
                f"Neto: {r.get('neto', '')}h<extra></extra>"
            ),
            showlegend=False, text="PeYa", textposition="inside",
            insidetextanchor="middle", textfont=dict(size=10, color="white"),
        ))

    tick_horas = list(range(8, 28))
    tick_text = [("00:00 (+1)" if h % 24 == 0 else f"{h % 24:02d}:00") for h in tick_horas]
    fig.update_layout(
        title=dict(text=f"📊 Gantt Semanal — {semana_label}", font=dict(size=18), x=0.5),
        barmode="overlay",
        xaxis=dict(range=[8, 28], tickvals=tick_horas, ticktext=tick_text, title="Horario",
                   gridcolor="rgba(128,128,128,0.25)"),
        yaxis=dict(categoryarray=list(reversed(DIAS_ORDEN)), categoryorder="array", title=""),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        height=430, margin=dict(l=10, r=10, t=60, b=40), bargap=0.35,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.add_vline(x=12, line_dash="dot", line_color="rgba(128,128,128,0.35)", line_width=1)
    # Trazas fantasma solo para la leyenda.
    fig.add_trace(go.Bar(x=[0], y=["Lunes"], base=[8], orientation="h",
                         marker_color="rgba(34,139,34,0.82)", name="Santo Tomás", showlegend=True))
    fig.add_trace(go.Bar(x=[0], y=["Lunes"], base=[8], orientation="h",
                         marker_color="rgba(200,30,30,0.82)", name="PeYa", showlegend=True))
    return fig


def generar_gantt_equipo(turnos: list[dict]) -> go.Figure:
    """Gantt de equipo: 4 trabajadores agrupados. `turnos` con trabajador/dia/entrada/salida/neto/extra/es_libre."""
    X_MIN, X_MAX = 9.0, 27.0
    fig = go.Figure()
    dias = list(reversed(DIAS_ORDEN))
    por_trab = {}
    for r in turnos:
        por_trab.setdefault(r.get("trabajador"), {})[r.get("dia")] = r

    for trabajador in TRABAJADORES:
        dias_trab = por_trab.get(trabajador)
        if not dias_trab:
            continue
        widths, bases, hovers = [], [], []
        for dia in dias:
            row = dias_trab.get(dia)
            if not row or row.get("es_libre"):
                widths.append(0)
                bases.append(X_MIN)
                hovers.append(f"{dia} — libre")
                continue
            hi, ho = hora_a_decimal(row.get("entrada")), hora_a_decimal(row.get("salida"))
            if hi is not None and ho is not None and ho <= hi:
                ho += 24
            ini = max(hi, X_MIN) if hi else X_MIN
            fin = min(ho, X_MAX) if ho else X_MIN
            widths.append(max(fin - ini, 0))
            bases.append(ini)
            hovers.append(
                f"<b>{trabajador}</b> — {dia}<br>Entrada: {_hm(row.get('entrada'))} "
                f"Salida: {_hm(row.get('salida'))}<br>Neto: {row.get('neto', 0)}h "
                f"Extras: {row.get('extra', 0)}h"
            )
        fig.add_trace(go.Bar(
            name=trabajador, y=dias, x=widths, base=bases, orientation="h",
            marker_color=COLORES_TRABAJADOR[trabajador],
            text=[f"{w:.1f}h" if w > 0 else "" for w in widths], textposition="inside",
            hovertemplate="%{customdata}<extra></extra>", customdata=hovers,
        ))

    ticks = list(range(int(X_MIN), int(X_MAX) + 1))
    fig.update_layout(
        barmode="group", height=450,
        xaxis=dict(range=[X_MIN, X_MAX], tickvals=ticks,
                   ticktext=[f"{h % 24:02d}:00" for h in ticks], title="Horario"),
        yaxis=dict(title=""), margin=dict(l=90, r=20, t=30, b=50),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig
