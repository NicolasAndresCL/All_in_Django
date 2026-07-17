"""Vista de Inicio: estado de conexión y resumen de cada módulo."""

from nicegui import ui

from nicegui_ui.api_client import APIError, get_client
from nicegui_ui.layout import banner_error, metric_card, shell

RECURSOS = {
    "Clases": "clases",
    "Turnos personales": "turnos-personales",
    "Turnos equipo": "turnos-equipo",
    "Tareas": "tareas",
    "Notas": "notas",
}

MODULOS_MD = """
**Módulos disponibles** (menú lateral):

- 📅 **Calendario** — clases de estudio y turnos personales.
- 👥 **LiveOps Equipo** — turnos del equipo + importación CSV/Excel.
- ✅ **Registro de Tareas** — actividades por proyecto + dashboard.
- 📝 **Notas** — notas Markdown/texto con exportación.
- 📺 **TV Chile** — grilla de canales (solo lectura).
"""


def render() -> None:
    with shell("Inicio"):
        ui.label("Panel visual sobre la API REST (Django + DRF).").classes("text-sm text-gray-500")
        api = get_client()

        if not api.ping():
            banner_error(
                f"No se pudo conectar con la API en {api.base}. Levanta el backend con "
                "`python manage.py runserver` o ajusta la variable de entorno API_BASE."
            )
            return

        if not api.autenticado():
            banner_error(
                "La API responde pero rechaza las credenciales (401). Define API_TOKEN "
                "(variable de entorno o nicegui_ui/.env). Crea el token con "
                "`python manage.py drf_create_token <usuario>` o desde el admin (Auth Token)."
            )
            return

        with ui.row().classes("items-center bg-green-900/30 rounded p-3 w-full"):
            ui.icon("check_circle").classes("text-green-400")
            ui.label(f"Conectado a la API en {api.base}")

        ui.label("Resumen").classes("text-lg font-medium")
        with ui.row().classes("gap-3 flex-wrap"):
            for etiqueta, recurso in RECURSOS.items():
                try:
                    metric_card(etiqueta, len(api.list(recurso)))
                except APIError as exc:
                    metric_card(etiqueta, "—", extra=f"error: {exc.status}")

        ui.separator()
        ui.markdown(MODULOS_MD)
