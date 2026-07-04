"""
core/horarios_export.py — PDFs con formato de horarios (fpdf2).

Portado de `all_in_one/core/horarios_logic.py`, pero desacoplado de pandas: cada
generador recibe listas de dicts (no DataFrames) y devuelve `bytes`. Los usan las
acciones `imprimir` de los ViewSets de calendario/liveops.

Nota fpdf2: las fuentes core ("Arial"→Helvetica) codifican en latin-1, así que el
texto se sanea con `_txt` para no romper con caracteres fuera de ese rango.
"""

from fpdf import FPDF

DIAS_ORDEN = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def _txt(valor) -> str:
    """Texto seguro para fuentes core de fpdf2 (latin-1); reemplaza lo no codificable."""
    return str(valor).encode("latin-1", "replace").decode("latin-1")


def _hms_a_hm(valor) -> str:
    """'HH:MM:SS' → 'HH:MM'; deja 'LIBRE'/otros tal cual."""
    s = str(valor)
    return s[:5] if len(s) >= 5 and s[2:3] == ":" else s


# ─── Horario de estudio (Santo Tomás) ───────────────────────────────────────
def generar_pdf_estudio(filas: list[dict], semana: str) -> bytes:
    """filas: [{dia, asignatura, entrada, salida, horas}]."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.set_text_color(0, 100, 0)
    pdf.cell(190, 10, _txt("HORARIO SANTO TOMÁS"), ln=True, align="C")
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "", 10)
    pdf.cell(190, 7, _txt(f"Semana: {semana}"), ln=True, align="C")
    pdf.ln(5)

    pdf.set_font("Arial", "B", 10)
    pdf.set_fill_color(200, 230, 200)
    for col, w in [("Día", 30), ("Asignatura", 80), ("Inicio", 25), ("Fin", 25), ("Horas", 30)]:
        pdf.cell(w, 8, _txt(col), 1, fill=True)
    pdf.ln()

    pdf.set_font("Arial", "", 9)
    total = 0.0
    for r in filas:
        total += float(r.get("horas") or 0)
        pdf.set_text_color(0, 80, 0)
        pdf.cell(30, 7, _txt(r.get("dia", "")), 1)
        pdf.cell(80, 7, _txt(r.get("asignatura", "")), 1)
        pdf.cell(25, 7, _txt(_hms_a_hm(r.get("entrada", ""))), 1)
        pdf.cell(25, 7, _txt(_hms_a_hm(r.get("salida", ""))), 1)
        pdf.cell(30, 7, _txt(f"{r.get('horas', 0)}h"), 1, ln=True)

    pdf.set_text_color(0, 0, 0)
    pdf.ln(3)
    pdf.set_font("Arial", "B", 11)
    pdf.cell(190, 8, _txt(f"Total Semanal: {round(total, 2)} h"), ln=True, align="R")
    return bytes(pdf.output())


# ─── Horario laboral (PedidosYa) ────────────────────────────────────────────
def generar_pdf_laboral(filas: list[dict], semana: str) -> bytes:
    """filas: [{dia, entrada, salida, bruto, neto, extra}]."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.set_text_color(160, 0, 0)
    pdf.cell(190, 10, _txt("HORARIO PEDIDOSYA"), ln=True, align="C")
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "", 10)
    pdf.cell(190, 7, _txt(f"Semana: {semana}"), ln=True, align="C")
    pdf.ln(5)

    pdf.set_font("Arial", "B", 10)
    pdf.set_fill_color(255, 210, 210)
    for col, w in [("Día", 30), ("Entrada", 28), ("Salida", 28), ("Bruto", 28), ("Neto", 28), ("Extra", 28)]:
        pdf.cell(w, 8, _txt(col), 1, fill=True)
    pdf.ln()

    pdf.set_font("Arial", "", 9)
    tot_bruto = tot_neto = tot_extra = 0.0
    for r in filas:
        tot_bruto += float(r.get("bruto") or 0)
        tot_neto += float(r.get("neto") or 0)
        tot_extra += float(r.get("extra") or 0)
        libre = r.get("es_libre")
        pdf.set_text_color(160, 0, 0)
        pdf.cell(30, 7, _txt(r.get("dia", "")), 1)
        pdf.cell(28, 7, _txt("LIBRE" if libre else _hms_a_hm(r.get("entrada", ""))), 1)
        pdf.cell(28, 7, _txt("LIBRE" if libre else _hms_a_hm(r.get("salida", ""))), 1)
        pdf.cell(28, 7, _txt(f"{r.get('bruto', 0)}h"), 1)
        pdf.cell(28, 7, _txt(f"{r.get('neto', 0)}h"), 1)
        pdf.cell(28, 7, _txt(f"{r.get('extra', 0)}h"), 1, ln=True)

    pdf.set_text_color(0, 0, 0)
    pdf.ln(3)
    pdf.set_font("Arial", "B", 11)
    pdf.cell(
        190, 8,
        _txt(f"Bruto: {round(tot_bruto, 2)}h  |  Neto: {round(tot_neto, 2)}h  |  "
             f"Extras: {round(tot_extra, 2)}h"),
        ln=True, align="R",
    )
    return bytes(pdf.output())


# ─── Turnos de equipo (LiveOps) ─────────────────────────────────────────────
def generar_pdf_equipo(filas: list[dict], titulo: str) -> bytes:
    """filas: [{trabajador?, dia, entrada, salida, bruto, neto, extra, es_libre}]."""
    columnas = [c for c in ("trabajador", "dia", "entrada", "salida", "bruto", "neto", "extra")
                if any(c in f for f in filas)] or ["dia", "entrada", "salida", "bruto", "neto", "extra"]
    encabezados = {"trabajador": "Trabajador", "dia": "Día", "entrada": "Entrada",
                   "salida": "Salida", "bruto": "Bruto", "neto": "Neto", "extra": "Extra"}

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, _txt(titulo), ln=True, align="C")
    pdf.ln(4)

    ancho = 190 // len(columnas)
    pdf.set_font("Arial", "B", 9)
    pdf.set_fill_color(220, 220, 220)
    for col in columnas:
        pdf.cell(ancho, 9, _txt(encabezados[col]), border=1, align="C", fill=True)
    pdf.ln()

    pdf.set_font("Arial", "", 9)
    tot_neto = tot_extra = 0.0
    for r in filas:
        tot_neto += float(r.get("neto") or 0)
        tot_extra += float(r.get("extra") or 0)
        libre = r.get("es_libre")
        for col in columnas:
            val = r.get(col, "")
            if col in ("entrada", "salida"):
                val = "LIBRE" if libre else _hms_a_hm(val)
            elif col in ("bruto", "neto", "extra"):
                val = f"{r.get(col, 0)}h"
            pdf.cell(ancho, 8, _txt(val), border=1)
        pdf.ln()

    pdf.ln(4)
    pdf.set_font("Arial", "B", 9)
    pdf.cell(0, 9, _txt(f"Total Neto: {round(tot_neto, 2)} h | Total Extras: {round(tot_extra, 2)} h"), ln=True)
    return bytes(pdf.output())


# ─── Horario maestro (estudio + trabajo combinados por día) ─────────────────
def generar_pdf_maestro(clases: list[dict], turnos: list[dict], semana: str) -> bytes:
    """Reporte unificado: por cada día lista bloques de ESTUDIO y TRABAJO."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(190, 10, _txt(f"Mi Horario Semanal - Semana: {semana}"), ln=True, align="C")
    pdf.ln(5)

    for dia in DIAS_ORDEN:
        clases_dia = [c for c in clases if c.get("dia") == dia]
        turnos_dia = [t for t in turnos if t.get("dia") == dia and not t.get("es_libre")]
        if not clases_dia and not turnos_dia:
            continue
        pdf.set_font("Arial", "B", 10)
        pdf.set_fill_color(230, 230, 230)
        pdf.cell(190, 8, _txt(f"--- {dia.upper()} ---"), 1, ln=True, fill=True)
        pdf.set_font("Arial", "", 9)
        for r in clases_dia:
            pdf.set_text_color(0, 80, 0)
            pdf.cell(30, 7, _txt("ESTUDIO"), 1)
            pdf.cell(90, 7, _txt(r.get("asignatura", "")), 1)
            pdf.cell(20, 7, _txt(_hms_a_hm(r.get("entrada", ""))), 1)
            pdf.cell(20, 7, _txt(_hms_a_hm(r.get("salida", ""))), 1)
            pdf.cell(30, 7, _txt(f"{r.get('horas', 0)}h"), 1, ln=True)
        for r in turnos_dia:
            pdf.set_text_color(180, 0, 0)
            pdf.cell(30, 7, _txt("TRABAJO"), 1)
            pdf.cell(90, 7, _txt("PeYa"), 1)
            pdf.cell(20, 7, _txt(_hms_a_hm(r.get("entrada", ""))), 1)
            pdf.cell(20, 7, _txt(_hms_a_hm(r.get("salida", ""))), 1)
            pdf.cell(30, 7, _txt(f"{r.get('neto', 0)}h"), 1, ln=True)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)
    return bytes(pdf.output())
