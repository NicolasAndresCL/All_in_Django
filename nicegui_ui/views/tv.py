"""Vista de TV Chile: grilla de canales (solo lectura, endpoint cacheado)."""

from nicegui import ui

from nicegui_ui.api_client import APIError, get_client
from nicegui_ui.layout import aviso, banner_error, shell


def render() -> None:
    with shell("TV Chile"):
        api = get_client()
        ui.label("Grilla de canales de TV chilena (datos cacheados 1h en el backend).") \
            .classes("text-sm text-gray-500")

        busqueda = ui.input(placeholder="Buscar canal…") \
            .props("outlined dense clearable debounce=400").classes("w-64")

        @ui.refreshable
        def grilla() -> None:
            try:
                data = api.tv_canales(busqueda.value or None)
            except APIError as exc:
                banner_error(f"No se pudieron obtener los canales: {exc.detalle or exc}")
                return

            canales = data.get("canales", [])
            ui.label(f"{data.get('total', len(canales))} canales").classes("font-bold")
            if not canales:
                aviso("No hay canales para la búsqueda.")
                return

            with ui.grid(columns=4).classes("w-full gap-3"):
                for canal in canales:
                    with ui.card().classes("p-3 items-center gap-2"):
                        if canal.get("logo"):
                            ui.image(canal["logo"]).classes("w-24 h-14 object-contain")
                        ui.label(canal["name"]).classes("font-bold text-center text-sm")
                        if canal.get("url"):
                            ui.link("Ver ↗", canal["url"], new_tab=True)

        busqueda.on_value_change(grilla.refresh)
        grilla()
