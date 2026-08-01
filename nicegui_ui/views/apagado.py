"""Vista de Apagado programado: temporizador de apagado/reinicio del PC local."""

from datetime import datetime

from nicegui import ui

from nicegui_ui import apagado
from nicegui_ui.layout import (
    aviso,
    banner_error,
    metric_card,
    notificar_error,
    notificar_ok,
    shell,
)

# Acciones que admiten temporizador (las inmediatas van en su propia sección).
_PROGRAMABLES = {k: a for k, a in apagado.ACCIONES.items() if a.programable}
_INMEDIATAS = {k: a for k, a in apagado.ACCIONES.items() if not a.programable}


@ui.refreshable
def _estado() -> None:
    """Programación vigente + cuenta atrás, o el aviso de que no hay nada pendiente."""
    prog = apagado.estado()
    if prog is None:
        aviso("No hay ningun apagado programado.")
        return

    etiqueta = apagado.ACCIONES[prog.accion].etiqueta
    with ui.row().classes("gap-3 flex-wrap items-center"):
        metric_card("Accion", etiqueta)
        metric_card("Hora", prog.cuando.strftime("%H:%M:%S"),
                    extra=prog.cuando.strftime("%d/%m/%Y"))
        restante = ui.label().classes("text-2xl font-bold text-orange-400")
        # La cuenta atrás la refresca un timer del cliente; el estado vive en el sistema.
        ui.timer(1.0, lambda: restante.set_text(
            apagado.formatear_restante(prog.restante())))
        ui.button("Cancelar", icon="cancel", on_click=_cancelar) \
            .props("color=negative outline")


def _cancelar() -> None:
    try:
        apagado.cancelar()
        notificar_ok("Apagado cancelado.")
    except apagado.ApagadoError as exc:
        notificar_error(str(exc))
    _estado.refresh()


def _programar(accion: str, segundos: int, forzar: bool) -> None:
    try:
        prog = apagado.programar(accion, segundos, forzar=forzar)
    except apagado.ApagadoError as exc:
        notificar_error(str(exc))
        return
    notificar_ok(f"{apagado.ACCIONES[accion].etiqueta} programado para "
                 f"{prog.cuando.strftime('%H:%M:%S')}.")
    _estado.refresh()


def render() -> None:
    with shell("Apagado"):
        ui.label("Temporizador de apagado del PC donde corre esta UI.") \
            .classes("text-sm text-gray-500")

        if not apagado.disponible():
            banner_error(
                "El apagado programado solo esta disponible en Windows y ejecutando la "
                "UI en tu equipo (con `nicegui_ui/run_app.bat`). Dentro de un contenedor "
                "apagaria el contenedor, no el PC."
            )
            return

        ui.label("Estado").classes("text-lg font-medium")
        _estado()

        ui.separator()
        ui.label("Programar").classes("text-lg font-medium")

        accion = ui.select({k: a.etiqueta for k, a in _PROGRAMABLES.items()},
                           value="apagar", label="Accion").classes("w-56")
        forzar = ui.checkbox("Forzar cierre de aplicaciones (/f)")
        ui.label("Con /f Windows cierra los programas sin esperar a que guarden.") \
            .classes("text-xs text-gray-500")

        with ui.row().classes("gap-2 flex-wrap items-center"):
            for minutos in apagado.PRESETS:
                ui.button(f"{minutos} min",
                          on_click=lambda m=minutos: _programar(
                              accion.value, m * 60, forzar.value)) \
                    .props("outline")

        with ui.row().classes("gap-2 items-end"):
            mins = ui.number("Minutos", value=45, min=0, precision=0).classes("w-32")
            ui.button("Programar", icon="timer",
                      on_click=lambda: _programar(
                          accion.value, int(mins.value or 0) * 60, forzar.value))

        with ui.row().classes("gap-2 items-end"):
            hora = ui.input("A una hora (HH:MM)", value="23:30").classes("w-40")
            ui.button("Programar a esa hora", icon="schedule",
                      on_click=lambda: _programar_a_hora(hora.value, accion.value,
                                                         forzar.value))

        ui.separator()
        ui.label("Inmediato").classes("text-lg font-medium")
        ui.label("Sin temporizador y sin vuelta atras: se ejecuta al pulsar.") \
            .classes("text-xs text-gray-500")
        with ui.row().classes("gap-2 flex-wrap"):
            for clave, cfg in _INMEDIATAS.items():
                ui.button(cfg.etiqueta,
                          on_click=lambda c=clave: _programar(c, 0, forzar.value)) \
                    .props("outline color=negative")


def _programar_a_hora(texto: str, accion: str, forzar: bool) -> None:
    """Convierte 'HH:MM' a un retardo en segundos y delega en `_programar`."""
    try:
        objetivo = datetime.strptime((texto or "").strip(), "%H:%M").time()
    except ValueError:
        notificar_error("Hora invalida: usa el formato HH:MM (por ejemplo 23:30).")
        return
    _programar(accion, apagado.segundos_hasta(objetivo), forzar)
