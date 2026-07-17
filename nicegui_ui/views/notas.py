"""Vista de Notas: crear, editar, previsualizar y exportar (md/txt)."""

from nicegui import ui

from nicegui_ui.api_client import APIError, get_client
from nicegui_ui.layout import banner_error, notificar_error, notificar_ok, shell

FORMATOS = {"md": "Markdown", "txt": "Texto plano"}


def render() -> None:
    with shell("Notas"):
        api = get_client()
        estado = {"sel": None}  # id de la nota seleccionada (None = nueva)

        @ui.refreshable
        def contenido() -> None:
            try:
                notas = api.list("notas")
            except APIError as exc:
                banner_error(f"No se pudieron cargar las notas: {exc}")
                notas = []

            opciones = {None: "— Nueva —"}
            opciones.update({n["id"]: f"#{n['id']} · {n['titulo'] or 'sin título'}" for n in notas})
            if estado["sel"] not in opciones:
                estado["sel"] = None
            nota = next((n for n in notas if n["id"] == estado["sel"]), None)

            with ui.row().classes("w-full gap-6 items-start no-wrap"):
                # -- lista / selección ------------------------------------
                with ui.column().classes("w-64 shrink-0"):
                    ui.label("Tus notas").classes("text-lg font-medium")

                    def cambiar(e) -> None:
                        estado["sel"] = e.value
                        contenido.refresh()

                    ui.radio(opciones, value=estado["sel"], on_change=cambiar)

                # -- editor -----------------------------------------------
                with ui.column().classes("grow"):
                    ui.label("Editar" if nota else "Crear nota").classes("text-lg font-medium")
                    titulo = ui.input("Título", value=(nota or {}).get("titulo", "")) \
                        .props("outlined dense").classes("w-full")
                    formato = ui.select(FORMATOS, value=(nota or {}).get("formato", "md"),
                                        label="Formato").props("outlined dense").classes("w-40")
                    cuerpo = ui.textarea("Contenido", value=(nota or {}).get("contenido", "")) \
                        .props("outlined input-style=\"min-height: 220px\"").classes("w-full")

                    def guardar() -> None:
                        payload = {"titulo": titulo.value, "contenido": cuerpo.value,
                                   "formato": formato.value}
                        try:
                            if nota:
                                api.update("notas", nota["id"], payload)
                            else:
                                creada = api.create("notas", payload)
                                estado["sel"] = creada["id"]
                            notificar_ok("Nota guardada.")
                            contenido.refresh()
                        except APIError as exc:
                            notificar_error(f"Error al guardar: {exc.detalle or exc}")

                    def eliminar() -> None:
                        with ui.dialog() as dlg, ui.card():
                            ui.label(f"¿Eliminar la nota #{nota['id']}?")
                            with ui.row():
                                ui.button("Cancelar", on_click=dlg.close).props("flat")

                                def confirmar() -> None:
                                    try:
                                        api.delete("notas", nota["id"])
                                        estado["sel"] = None
                                        notificar_ok("Nota eliminada.")
                                        dlg.close()
                                        contenido.refresh()
                                    except APIError as exc:
                                        notificar_error(f"Error al eliminar: {exc}")

                                ui.button("Eliminar", color="negative", on_click=confirmar)
                        dlg.open()

                    with ui.row().classes("items-center gap-2"):
                        ui.button("💾 Guardar", on_click=guardar).props("color=primary")
                        if nota:
                            ui.button("🗑️ Eliminar", on_click=eliminar).props("flat color=negative")
                            fmt_dl = ui.select(["md", "txt"], value=nota["formato"]) \
                                .props("outlined dense").classes("w-24")

                            def descargar() -> None:
                                try:
                                    data, _ = api.download(f"notas/{nota['id']}/exportar/",
                                                           fmt=fmt_dl.value)
                                    ui.download(data, f"nota_{nota['id']}.{fmt_dl.value}")
                                except APIError as exc:
                                    notificar_error(f"Error al exportar: {exc}")

                            ui.button("⬇️ Descargar", on_click=descargar).props("flat")

                    # -- previsualización en vivo --------------------------
                    ui.separator()
                    ui.label("Previsualización").classes("text-xs text-gray-500")
                    preview = ui.markdown(cuerpo.value or "")

                    def actualizar_preview() -> None:
                        texto = cuerpo.value or ""
                        preview.set_content(
                            texto if formato.value == "md" else f"```text\n{texto}\n```"
                        )

                    cuerpo.on_value_change(actualizar_preview)
                    formato.on_value_change(actualizar_preview)
                    actualizar_preview()

        contenido()
