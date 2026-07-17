"""Vista de LiveOps: turnos del equipo, importación CSV/Excel y exportación."""

from datetime import date, timedelta

from nicegui import ui

from nicegui_ui.api_client import APIError, get_client
from nicegui_ui.gantt import generar_gantt_equipo
from nicegui_ui.layout import aviso, banner_error, grafico, metric_card, notificar_error, notificar_ok, shell, tabla

DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
TRABAJADORES = ["Manu", "Jorge", "Babi", "Nico"]
TODOS = "(todos)"


def _lunes(d: date) -> str:
    return (d - timedelta(days=d.weekday())).isoformat()


def render() -> None:
    with shell("LiveOps Equipo"):
        api = get_client()
        estado = {"usar_semana": False, "semana": _lunes(date.today()), "trabajador": TODOS}

        def params() -> dict:
            p = {}
            if estado["usar_semana"]:
                p["semana_inicio"] = estado["semana"]
            if estado["trabajador"] != TODOS:
                p["trabajador"] = estado["trabajador"]
            return p

        # ------------------------------------------------------- filtros
        with ui.card().classes("p-3 w-full"):
            with ui.row().classes("gap-4 items-center flex-wrap"):
                chk = ui.checkbox(
                    "Filtrar por semana", value=estado["usar_semana"],
                    on_change=lambda e: (estado.update(usar_semana=e.value), listado.refresh()),
                )
                sem = ui.input("Semana (lunes)", value=estado["semana"],
                               on_change=lambda e: (estado.update(semana=e.value),
                                                    listado.refresh())) \
                    .props("type=date outlined dense")
                sem.bind_enabled_from(chk, "value")
                ui.select([TODOS] + TRABAJADORES, value=estado["trabajador"], label="Trabajador",
                          on_change=lambda e: (estado.update(trabajador=e.value),
                                               listado.refresh())) \
                    .props("outlined dense").classes("w-44")

        # ------------------------------------------------------- listado
        @ui.refreshable
        def listado() -> None:
            try:
                turnos = api.list("turnos-equipo", **params())
            except APIError as exc:
                banner_error(f"No se pudieron cargar los turnos: {exc}")
                return
            if not turnos:
                aviso("Sin turnos para los filtros actuales.")
                return
            tabla(turnos)
            with ui.row().classes("gap-3"):
                metric_card("Turnos", len(turnos))
                metric_card("Horas netas", round(sum(t.get("neto", 0) for t in turnos), 2))
                metric_card("Horas extra", round(sum(t.get("extra", 0) for t in turnos), 2))
            grafico(generar_gantt_equipo(turnos))

        listado()
        ui.separator()

        with ui.row().classes("w-full gap-6 items-start no-wrap"):
            # -- alta manual ---------------------------------------------
            with ui.column().classes("w-1/2"):
                ui.label("Nuevo turno").classes("text-lg font-medium")
                f_sem = ui.input("Semana (lunes)", value=_lunes(date.today())) \
                    .props("type=date outlined dense")
                with ui.row().classes("gap-3"):
                    f_trab = ui.select(TRABAJADORES, value=TRABAJADORES[0], label="Trabajador") \
                        .props("outlined dense").classes("w-40")
                    f_dia = ui.select(DIAS, value=DIAS[0], label="Día") \
                        .props("outlined dense").classes("w-40")
                f_libre = ui.checkbox("Día libre", value=False)
                with ui.row().classes("gap-3"):
                    f_in = ui.input("Entrada", value="09:00").props("type=time outlined dense")
                    f_out = ui.input("Salida", value="18:00").props("type=time outlined dense")
                # disabled reactivo (con st.form no reaccionaba hasta el submit).
                f_in.bind_enabled_from(f_libre, "value", backward=lambda v: not v)
                f_out.bind_enabled_from(f_libre, "value", backward=lambda v: not v)

                def crear() -> None:
                    payload = {"semana_inicio": f_sem.value, "trabajador": f_trab.value,
                               "dia": f_dia.value, "es_libre": f_libre.value}
                    if not f_libre.value:
                        if not f_in.value or not f_out.value:
                            notificar_error("Define entrada y salida (o marca Día libre).")
                            return
                        payload["entrada"] = f"{f_in.value}:00"
                        payload["salida"] = f"{f_out.value}:00"
                    try:
                        api.create("turnos-equipo", payload)  # upsert por (semana, trab, día)
                        notificar_ok("Turno guardado.")
                        listado.refresh()
                    except APIError as exc:
                        notificar_error(f"Error al crear: {exc.detalle or exc}")

                ui.button("Crear turno", on_click=crear).props("color=primary")

            # -- importar / exportar --------------------------------------
            with ui.column().classes("grow"):
                ui.label("Importar / Exportar").classes("text-lg font-medium")
                ui.label("Importar turnos (CSV o Excel con Fecha, Agente, Entrada, Salida):") \
                    .classes("text-xs text-gray-500")

                def importar(e) -> None:
                    try:
                        res = api.upload("turnos-equipo", "importar",
                                         e.name, e.content.read())
                        msg = f"Importadas {res.get('importadas', 0)} filas."
                        if res.get("errores"):
                            msg += f" Errores: {'; '.join(res['errores'][:3])}"
                        notificar_ok(msg)
                        listado.refresh()
                    except APIError as exc:
                        notificar_error(f"Error al importar: {exc.detalle or exc}")

                ui.upload(on_upload=importar, auto_upload=True, max_files=1) \
                    .props("accept=.csv,.xlsx,.xls").classes("w-full")

                ui.label("Exportar / imprimir (respeta los filtros de arriba):") \
                    .classes("text-xs text-gray-500 q-mt-md")

                def exportar(formato: str) -> None:
                    ext = "xlsx" if formato == "excel" else "pdf"
                    try:
                        contenido, _ = api.download("turnos-equipo/exportar/",
                                                    formato=formato, **params())
                        ui.download(contenido, f"turnos_equipo.{ext}")
                    except APIError as exc:
                        notificar_error(f"Error: {exc}")

                def pdf_formato() -> None:
                    try:
                        data, _ = api.download("turnos-equipo/imprimir/", **params())
                        ui.download(data, "Horario_equipo.pdf")
                    except APIError as exc:
                        notificar_error(f"Error: {exc}")

                with ui.row().classes("gap-2"):
                    ui.button("EXCEL", on_click=lambda: exportar("excel")).props("outline")
                    ui.button("PDF", on_click=lambda: exportar("pdf")).props("outline")
                    ui.button("PDF con formato", on_click=pdf_formato).props("outline")
