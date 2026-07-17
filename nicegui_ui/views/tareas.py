"""Vista de Registro de Tareas: dashboard (6 métricas + 6 gráficos), CRUD y filtro."""

from datetime import date

from nicegui import ui

from nicegui_ui.api_client import APIError, get_client
from nicegui_ui.charts import construir_figuras
from nicegui_ui.layout import (PLOTLY_TEMPLATE, aviso, banner_error, grafico, metric_card,
                    notificar_error, notificar_ok, shell, tabla)

NUEVO_P, NUEVA_T = "➕ Nuevo proyecto…", "➕ Nueva tarea…"
TODOS = "(todos)"

FIGURAS = [
    ("jerarquia", "Jerarquía Proyecto / Tarea"),
    ("esfuerzo", "Esfuerzo por Proyecto"),
    ("intensidad", "Intensidad Diaria"),
    ("semanal", "Productividad Semanal"),
    ("dia_semana", "Actividad por Día de la Semana"),
    ("acumulado", "Progreso Acumulado"),
]


def render() -> None:
    with shell("Registro de Tareas"):
        api = get_client()
        estado = {
            "todas": [], "error": None, "filtro": TODOS,
            "fecha": date.today().isoformat(),
            "p_sel": None, "p_new": "", "t_sel": None, "t_new": "",
            "h": 1, "m": 0,
        }

        def cargar_datos() -> None:
            try:
                estado["todas"] = api.list("tareas")
                estado["error"] = None
            except APIError as exc:
                estado["todas"], estado["error"] = [], str(exc)

        def proyectos() -> list[str]:
            return sorted({t["proyecto"] for t in estado["todas"]})

        # ------------------------------------------------------- dashboard
        @ui.refreshable
        def dashboard() -> None:
            ui.label("Resumen").classes("text-lg font-medium")
            try:
                resumen = api.action("tareas", "resumen")
            except APIError as exc:
                banner_error(f"No se pudo cargar el resumen: {exc}")
                return
            if not resumen.get("tareas"):
                aviso("Aún no hay tareas registradas: agrega una para ver el dashboard.")
                return

            with ui.row().classes("gap-3 flex-wrap"):
                metric_card("Tareas Totales", resumen["tareas"])
                metric_card("Proyectos Activos", resumen["proyectos"])
                metric_card("Horas Acumuladas", f"{resumen['horas_total']:.1f} h")
                racha = resumen["racha_dias"]
                metric_card("Racha Actual", f"{racha} días",
                            extra="🔥 activa" if racha else None)
                metric_card("Promedio Diario", f"{resumen['promedio_diario']:.1f} h")
                metric_card("Promedio Semanal", f"{resumen['promedio_semanal']:.1f} h")

            figs = construir_figuras(resumen, PLOTLY_TEMPLATE)
            with ui.grid(columns=2).classes("w-full gap-4"):
                for clave, titulo in FIGURAS:
                    with ui.card().classes("p-3 w-full"):
                        ui.label(titulo).classes("font-medium")
                        if figs[clave] is not None:
                            grafico(figs[clave])
                        else:
                            ui.label("Sin datos suficientes.").classes("text-xs text-gray-500")

        # ------------------------------------------------ listado con filtro
        @ui.refreshable
        def listado() -> None:
            ui.label("Registros").classes("text-lg font-medium")
            if estado["error"]:
                banner_error(f"No se pudieron cargar las tareas: {estado['error']}")
                return

            def cambia_filtro(e) -> None:
                estado["filtro"] = e.value
                listado.refresh()
                borrar.refresh()

            ui.select([TODOS] + proyectos(), value=estado["filtro"],
                      label="Filtrar por proyecto", on_change=cambia_filtro) \
                .props("outlined dense").classes("w-64")
            registros = _filtrados(estado)
            if registros:
                tabla(registros)
            else:
                aviso("Sin registros para el filtro actual.")

        # --------------------------------------------------------- alta
        @ui.refreshable
        def alta() -> None:
            ui.label("Nueva tarea").classes("text-lg font-medium")
            ui.label("Elige un proyecto/tarea existente para reutilizarlo, o crea uno nuevo.") \
                .classes("text-xs text-gray-500")

            proys = proyectos()
            opciones_p = proys + [NUEVO_P]
            if estado["p_sel"] not in opciones_p:
                estado["p_sel"] = proys[0] if proys else NUEVO_P

            with ui.row().classes("gap-3 items-end flex-wrap"):
                ui.input("Fecha", value=estado["fecha"],
                         on_change=lambda e: estado.update(fecha=e.value)) \
                    .props("type=date outlined dense")

                def cambia_p(e) -> None:
                    estado.update(p_sel=e.value, t_sel=None)
                    alta.refresh()

                ui.select(opciones_p, value=estado["p_sel"], label="Proyecto",
                          on_change=cambia_p).props("outlined dense").classes("w-56")
                if estado["p_sel"] == NUEVO_P:
                    ui.input("Nombre del proyecto", value=estado["p_new"],
                             on_change=lambda e: estado.update(p_new=e.value)) \
                        .props("outlined dense")

            # Tareas ya usadas en ese proyecto → referencia para no reescribirlas.
            tareas_prev = (sorted({t["tarea"] for t in estado["todas"]
                                   if t["proyecto"] == estado["p_sel"]})
                           if estado["p_sel"] != NUEVO_P else [])
            opciones_t = tareas_prev + [NUEVA_T]
            if estado["t_sel"] not in opciones_t:
                estado["t_sel"] = opciones_t[0]

            with ui.row().classes("gap-3 items-end flex-wrap"):
                def cambia_t(e) -> None:
                    estado.update(t_sel=e.value)
                    alta.refresh()

                ui.select(opciones_t, value=estado["t_sel"], label="Tarea",
                          on_change=cambia_t).props("outlined dense").classes("w-56")
                if estado["t_sel"] == NUEVA_T:
                    ui.input("Nombre de la tarea", value=estado["t_new"],
                             on_change=lambda e: estado.update(t_new=e.value)) \
                        .props("outlined dense").classes("w-64")
                ui.number("Horas", value=estado["h"], min=0, max=23, format="%d",
                          on_change=lambda e: estado.update(h=int(e.value or 0))) \
                    .props("outlined dense").classes("w-24")
                ui.number("Minutos", value=estado["m"], min=0, max=59, format="%d",
                          on_change=lambda e: estado.update(m=int(e.value or 0))) \
                    .props("outlined dense").classes("w-24")
                ui.button("Crear tarea", on_click=crear).props("color=primary")

        def crear() -> None:
            proyecto = estado["p_new"] if estado["p_sel"] == NUEVO_P else estado["p_sel"]
            tarea = estado["t_new"] if estado["t_sel"] == NUEVA_T else estado["t_sel"]
            if not str(proyecto or "").strip() or not str(tarea or "").strip():
                notificar_error("Completa proyecto y tarea.")
                return
            if estado["h"] == 0 and estado["m"] == 0:
                notificar_error("La duración no puede ser 0.")
                return
            try:
                api.create("tareas", {
                    "fecha": estado["fecha"],
                    "proyecto": proyecto,
                    "tarea": tarea,
                    # DurationField DRF acepta "HH:MM:SS".
                    "duracion": f"{estado['h']:02d}:{estado['m']:02d}:00",
                })
                notificar_ok("Tarea creada.")
                recargar_todo()
            except APIError as exc:
                notificar_error(f"Error al crear: {exc.detalle or exc}")

        # --------------------------------------------------------- borrar
        @ui.refreshable
        def borrar() -> None:
            registros = _filtrados(estado)
            if not registros:
                return
            with ui.expansion("Eliminar registro").classes("w-full"):
                opciones = {
                    r["id"]: f"#{r['id']} · {r['fecha']} · {r['proyecto']} · {r['tarea']}"
                    for r in registros
                }
                sel = ui.select(opciones, value=next(iter(opciones))) \
                    .props("outlined dense").classes("w-full")

                def eliminar() -> None:
                    try:
                        api.delete("tareas", sel.value)
                        notificar_ok("Eliminado.")
                        recargar_todo()
                    except APIError as exc:
                        notificar_error(f"Error al eliminar: {exc}")

                ui.button("Eliminar", color="negative", on_click=eliminar).props("flat")

        def recargar_todo() -> None:
            cargar_datos()
            dashboard.refresh()
            listado.refresh()
            alta.refresh()
            borrar.refresh()

        # ------------------------------------------------------- página
        cargar_datos()
        dashboard()
        ui.separator()
        listado()
        ui.separator()
        alta()
        borrar()


def _filtrados(estado: dict) -> list[dict]:
    """Registros según el filtro de proyecto (client-side: `todas` ya trae TODO paginado)."""
    if estado["filtro"] == TODOS:
        return estado["todas"]
    return [t for t in estado["todas"] if t["proyecto"] == estado["filtro"]]
