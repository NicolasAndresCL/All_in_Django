"""Vista de Inicio: estado de conexión y resumen de cada módulo."""

from nicegui import ui

from nicegui_ui.api_client import APIError, get_client
from nicegui_ui.layout import banda_tripulacion, banner_error, metric_card, shell

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
        # Portada: la tripulación al completo. Va antes de los cortes por error de
        # conexión para que la página tenga identidad incluso si la API no responde.
        banda_tripulacion()
        api = get_client()

        # Una sola petición decide las tres cosas: si la API está viva, si acepta las
        # credenciales y —cuando no— por qué. Antes eran dos (`ping` + `autenticado`)
        # contra la misma URL, y el doble de gasto contra el rate limit.
        ok, status = api.estado_auth()
        if status is None:
            banner_error(
                f"No se pudo conectar con la API en {api.base}. Levanta el backend con "
                "`python manage.py runserver` o ajusta la variable de entorno API_BASE."
            )
            return
        if not ok:
            banner_error(_motivo(status, api.tiene_token))
            return

        with ui.row().classes("items-center bg-green-900/30 rounded p-3 w-full"):
            ui.icon("check_circle").classes("text-green-400")
            ui.label(f"Conectado a la API en {api.base}")

        ui.label("Resumen").classes("text-lg font-medium")
        with ui.row().classes("gap-3 flex-wrap"):
            for etiqueta, recurso in RECURSOS.items():
                try:
                    # `contar` = 1 petición por recurso. Con `len(api.list(...))` la
                    # portada se descargaba las 543 tareas (11 páginas) para pintar un
                    # número, y unas pocas recargas agotaban el rate limit de la API.
                    metric_card(etiqueta, api.contar(recurso))
                except APIError as exc:
                    metric_card(etiqueta, "—", extra=f"error: {exc.status}")

        ui.separator()
        ui.markdown(MODULOS_MD)


def _motivo(status: int | None, tiene_token: bool) -> str:
    """Mensaje del banner según lo que respondió la API.

    Un solo texto para todos los fallos mandaba a revisar el token aunque el problema
    fuese otro (el caso real: 429 por rate limit anunciado como credenciales inválidas).
    """
    if status in (401, 403) and not tiene_token:
        return (
            "La API responde pero exige autenticación y la UI no tiene token. Define "
            "API_TOKEN (variable de entorno o nicegui_ui/.env) y recarga. Crea el token "
            "con `python manage.py drf_create_token <usuario>` o desde el admin "
            "(Auth Token)."
        )
    if status in (401, 403):
        return (
            f"La API rechaza el token de la UI ({status}). Suele pasar cuando el token "
            "es de otra base de datos (p. ej. se creó en SQLite y la API ya corre sobre "
            "Postgres) o el usuario dueño del token se borró. Genera uno nuevo con "
            "`python manage.py drf_create_token <usuario>` y actualiza API_TOKEN en "
            "nicegui_ui/.env."
        )
    if status == 429:
        return (
            "Límite de peticiones alcanzado (429): la API aplica rate limiting (300/min "
            "por usuario). No es un problema de credenciales — espera un minuto y "
            "recarga, o sube THROTTLE_USER en el .env del backend."
        )
    return f"La API respondió {status} al comprobar las credenciales en {get_client().base}."
