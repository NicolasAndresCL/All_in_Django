"""Vista de Calendario: clases y turnos personales (CRUD, copiar semana, PDF, Gantt).

La grilla semanal de turnos usa estado Python directo (referencias a los widgets y
`set_value`), sin la siembra de session_state que exigía Streamlit: "cargar desde otra
semana" simplemente asigna los valores al formulario, editable antes de guardar.
"""

from datetime import date, datetime, timedelta

from nicegui import ui

from nicegui_ui.api_client import APIError, get_client
from nicegui_ui.gantt import generar_gantt
from nicegui_ui.layout import aviso, banner_error, grafico, metric_card, notificar_error, notificar_ok, shell, tabla

DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def _lunes_iso(valor: str | date) -> str:
    """Lunes (ISO) de la semana de `valor` (date o 'YYYY-MM-DD')."""
    d = valor if isinstance(valor, date) else datetime.strptime(valor[:10], "%Y-%m-%d").date()
    return (d - timedelta(days=d.weekday())).isoformat()


def _semanas(items: list[dict]) -> list[str]:
    """Semanas distintas presentes en `items`, más recientes primero."""
    return sorted({i["semana_inicio"] for i in items}, reverse=True)


def render() -> None:
    with shell("Calendario"):
        api = get_client()
        refrescos: dict[str, callable] = {}  # registro cruzado entre pestañas

        with ui.tabs().classes("w-full") as tabs:
            t_clases = ui.tab("Clases")
            t_turnos = ui.tab("Turnos personales")
            t_impr = ui.tab("Impresión y Gantt")
        with ui.tab_panels(tabs, value=t_clases).classes("w-full"):
            with ui.tab_panel(t_clases):
                _tab_clases(api, refrescos)
            with ui.tab_panel(t_turnos):
                _tab_turnos(api, refrescos)
            with ui.tab_panel(t_impr):
                _tab_impresion(api, refrescos)


# ─────────────────────────────────────────────────────────────────── Clases ──
def _tab_clases(api, refrescos: dict) -> None:
    ui.label("Clases (Santo Tomás)").classes("text-lg font-medium")

    @ui.refreshable
    def contenido() -> None:
        try:
            clases = api.list("clases")
        except APIError as exc:
            banner_error(f"No se pudieron cargar las clases: {exc}")
            return

        # -- copiar / basar en otra semana ---------------------------------
        with ui.expansion("📋 Copiar / basar en otra semana").classes("w-full"):
            semanas = _semanas(clases)
            if not semanas:
                aviso("Aún no hay otras semanas para copiar.")
            else:
                origen = ui.select(semanas, value=semanas[0], label="Semana origen") \
                    .props("outlined dense").classes("w-44")
                destino = ui.input("Semana destino (lunes)", value=_lunes_iso(date.today())) \
                    .props("type=date outlined dense")
                ui.label("⚠️ Reemplaza lo que haya en la semana destino.") \
                    .classes("text-xs text-orange-400")

                def copiar() -> None:
                    try:
                        res = api.post_action("clases", "copiar_semana", {
                            "origen": origen.value, "destino": _lunes_iso(destino.value),
                        })
                        notificar_ok(f"{res['copiadas']} registros copiados a {res['destino']}.")
                        _refrescar(refrescos, "clases", "impresion")
                    except APIError as exc:
                        notificar_error(f"Error al copiar: {exc.detalle or exc}")

                ui.button("📥 Copiar", on_click=copiar).props("color=primary flat")

        # -- nueva clase -----------------------------------------------------
        ui.label("Nueva clase").classes("font-medium q-mt-md")
        with ui.row().classes("gap-3 items-end flex-wrap"):
            semana = ui.input("Semana (lunes)", value=_lunes_iso(date.today())) \
                .props("type=date outlined dense")
            dia = ui.select(DIAS, value=DIAS[0], label="Día").props("outlined dense").classes("w-36")
            asignatura = ui.input("Asignatura").props("outlined dense").classes("w-52")
            entrada = ui.input("Entrada", value="08:00").props("type=time outlined dense")
            salida = ui.input("Salida", value="10:00").props("type=time outlined dense")

            def crear() -> None:
                if not (asignatura.value or "").strip():
                    notificar_error("Indica la asignatura.")
                    return
                try:
                    api.create("clases", {
                        "semana_inicio": _lunes_iso(semana.value), "dia": dia.value,
                        "asignatura": asignatura.value,
                        "entrada": f"{entrada.value}:00", "salida": f"{salida.value}:00",
                    })
                    notificar_ok("Clase creada.")
                    _refrescar(refrescos, "clases", "impresion")
                except APIError as exc:
                    notificar_error(f"Error al crear: {exc.detalle or exc}")

            ui.button("Crear clase", on_click=crear).props("color=primary")

        # -- tabla de registros (debajo del formulario) ----------------------
        if clases:
            ui.label("Registros").classes("font-medium q-mt-md")
            tabla(clases)
        else:
            aviso("Sin clases registradas.")

        # -- eliminar ---------------------------------------------------------
        if clases:
            with ui.expansion("Eliminar registro").classes("w-full"):
                opciones = {
                    c["id"]: f"#{c['id']} · {c['semana_inicio']} · {c['dia']} · {c['asignatura']}"
                    for c in clases
                }
                sel = ui.select(opciones, value=next(iter(opciones))) \
                    .props("outlined dense").classes("w-full")

                def eliminar() -> None:
                    try:
                        api.delete("clases", sel.value)
                        notificar_ok("Eliminado.")
                        _refrescar(refrescos, "clases", "impresion")
                    except APIError as exc:
                        notificar_error(f"Error al eliminar: {exc}")

                ui.button("Eliminar", color="negative", on_click=eliminar).props("flat")

    refrescos["clases"] = contenido.refresh
    contenido()


# ─────────────────────────────────────────────────────── Turnos personales ──
def _tab_turnos(api, refrescos: dict) -> None:
    """Grilla semanal editable (upsert por día), estilo all_in_one."""
    ui.label("Turnos personales (PedidosYa)").classes("text-lg font-medium")
    estado = {"semana": _lunes_iso(date.today())}
    grilla: dict[str, dict] = {}  # dia -> {"libre": widget, "in": widget, "out": widget}

    def turnos_de(semana: str) -> dict[str, dict]:
        try:
            return {t["dia"]: t for t in api.list("turnos-personales", semana_inicio=semana)}
        except APIError as exc:
            notificar_error(f"No se pudieron cargar los turnos: {exc}")
            return {}

    def sembrar(fuente: dict[str, dict], libre_si_falta: bool) -> None:
        """Precarga la grilla desde `fuente` {dia: turno} — solo asignar .value."""
        for d in DIAS:
            t = fuente.get(d)
            libre = bool(t["es_libre"]) if t else libre_si_falta
            grilla[d]["libre"].value = libre
            grilla[d]["in"].value = (t["entrada"][:5] if t and not libre and t.get("entrada")
                                     else "18:00")
            grilla[d]["out"].value = (t["salida"][:5] if t and not libre and t.get("salida")
                                      else "23:00")

    # -- selector de semana ----------------------------------------------------
    def cambia_semana(e) -> None:
        if not e.value:
            return
        estado["semana"] = _lunes_iso(e.value)
        sembrar(turnos_de(estado["semana"]), libre_si_falta=False)
        resumen.refresh()

    ui.input("Semana a editar (lunes)", value=estado["semana"], on_change=cambia_semana) \
        .props("type=date outlined dense")

    # -- cargar desde otra semana (al formulario, editable) ---------------------
    with ui.expansion("📋 Cargar desde otra semana (para editar antes de guardar)") \
            .classes("w-full"):
        try:
            todas = api.list("turnos-personales")
        except APIError:
            todas = []
        otras = [s for s in _semanas(todas)]
        if not otras:
            aviso("No hay otras semanas para cargar.")
        else:
            origen = ui.select(otras, value=otras[0], label="Semana origen") \
                .props("outlined dense").classes("w-44")
            ui.label("Trae esos horarios al formulario; edítalos y luego pulsa Guardar.") \
                .classes("text-xs text-gray-500")

            def cargar() -> None:
                sembrar(turnos_de(origen.value), libre_si_falta=True)
                notificar_ok(f"Horarios de {origen.value} cargados al formulario.")

            ui.button("📥 Cargar al formulario", on_click=cargar).props("flat color=primary")

    # -- grilla de 7 días --------------------------------------------------------
    ui.label("Configura la semana — marca Libre o define entrada/salida por día:") \
        .classes("font-medium")
    with ui.grid(columns=7).classes("w-full gap-2"):
        for d in DIAS:
            with ui.column().classes("items-stretch gap-1"):
                ui.label(d[:3]).classes("font-bold text-center")
                chk = ui.checkbox("Libre", value=False)
                ent = ui.input(value="18:00").props("type=time outlined dense")
                sal = ui.input(value="23:00").props("type=time outlined dense")
                ent.bind_enabled_from(chk, "value", backward=lambda v: not v)
                sal.bind_enabled_from(chk, "value", backward=lambda v: not v)
                grilla[d] = {"libre": chk, "in": ent, "out": sal}

    def guardar_semana() -> None:
        errores = []
        for d in DIAS:
            libre = grilla[d]["libre"].value
            payload = {"semana_inicio": estado["semana"], "dia": d, "es_libre": libre}
            if not libre:
                payload["entrada"] = f"{grilla[d]['in'].value}:00"
                payload["salida"] = f"{grilla[d]['out'].value}:00"
            try:
                api.create("turnos-personales", payload)  # upsert por (semana, día)
            except APIError as exc:
                errores.append(f"{d}: {exc.detalle or exc}")
        if errores:
            notificar_error("No se pudieron guardar algunos días: " + " · ".join(errores))
        else:
            notificar_ok(f"Semana {estado['semana']} guardada.")
        resumen.refresh()
        _refrescar(refrescos, "impresion")

    ui.button("💾 Guardar semana", on_click=guardar_semana).props("color=primary")

    # -- resumen de la semana (debajo del formulario) -----------------------------
    @ui.refreshable
    def resumen() -> None:
        ui.separator()
        por_dia = turnos_de(estado["semana"])
        if not por_dia:
            aviso("Sin turnos guardados en esta semana. Configúralos arriba y guarda.")
            return
        filas = list(por_dia.values())
        tabla(filas)
        with ui.row().classes("gap-3"):
            metric_card("Horas netas", round(sum(t.get("neto", 0) for t in filas), 2))
            metric_card("Horas extra", round(sum(t.get("extra", 0) for t in filas), 2))

    refrescos["turnos"] = resumen.refresh
    sembrar(turnos_de(estado["semana"]), libre_si_falta=False)
    resumen()


# ───────────────────────────────────────────────────────── Impresión y Gantt ──
def _tab_impresion(api, refrescos: dict) -> None:
    ui.label("Impresión y visualización").classes("text-lg font-medium")
    estado = {"semana": None}

    @ui.refreshable
    def contenido() -> None:
        try:
            clases = api.list("clases")
            turnos = api.list("turnos-personales")
        except APIError as exc:
            banner_error(f"No se pudieron cargar los datos: {exc}")
            return

        semanas = sorted(set(_semanas(clases)) | set(_semanas(turnos)), reverse=True)
        if not semanas:
            aviso("Registra clases o turnos para imprimir o graficar.")
            return
        if estado["semana"] not in semanas:
            estado["semana"] = semanas[0]

        def cambia(e) -> None:
            estado["semana"] = e.value
            contenido.refresh()

        ui.select(semanas, value=estado["semana"], label="Semana", on_change=cambia) \
            .props("outlined dense").classes("w-44")

        sem = estado["semana"]
        cls_sem = [c for c in clases if c["semana_inicio"] == sem]
        tur_sem = [t for t in turnos if t["semana_inicio"] == sem]

        h_est = round(sum(c.get("horas", 0) for c in cls_sem), 1)
        h_lab = round(sum(t.get("neto", 0) for t in tur_sem), 1)
        with ui.row().classes("gap-3"):
            metric_card("Carga académica", f"{h_est} h")
            metric_card("Carga laboral (neto)", f"{h_lab} h")
            metric_card("Ocupación total", f"{round(h_est + h_lab, 1)} h")

        grafico(generar_gantt(cls_sem, tur_sem, sem))

        ui.label("Descargar PDF").classes("font-medium")

        def pdf(path: str, nombre: str) -> None:
            try:
                data, _ = api.download(path, semana_inicio=sem)
                ui.download(data, nombre)
            except APIError as exc:
                notificar_error(f"Error al generar el PDF: {exc}")

        with ui.row().classes("gap-2"):
            ui.button("📄 Estudio",
                      on_click=lambda: pdf("clases/imprimir/", f"Estudio_{sem}.pdf")) \
                .props("outline")
            ui.button("📄 Laboral",
                      on_click=lambda: pdf("turnos-personales/imprimir/", f"PeYa_{sem}.pdf")) \
                .props("outline")
            ui.button("📄 Maestro",
                      on_click=lambda: pdf("clases/imprimir_maestro/", f"Master_{sem}.pdf")) \
                .props("outline")

    refrescos["impresion"] = contenido.refresh
    contenido()


def _refrescar(refrescos: dict, *claves: str) -> None:
    """Refresca las secciones registradas (si existen) tras una mutación."""
    for clave in claves:
        if clave in refrescos:
            refrescos[clave]()
