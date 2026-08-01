"""
Tests del apagado programado. `shutdown.exe` se mockea siempre (unittest.mock): la
suite corre en Linux en CI y, sobre todo, no queremos apagar la máquina de nadie.
"""

from datetime import datetime, time, timedelta
from unittest.mock import patch

import pytest

from nicegui_ui import apagado


@pytest.fixture
def shutdown():
    """subprocess.run mockeado devolviendo éxito; expone las llamadas hechas."""
    with patch("nicegui_ui.apagado.subprocess.run") as run:
        run.return_value.returncode = 0
        run.return_value.stdout = b""
        run.return_value.stderr = b""
        yield run


def _args(run) -> list[str]:
    return run.call_args.args[0]


# ─── cálculo de retardo (lógica pura) ────────────────────────────────────────
@pytest.mark.parametrize("ahora, objetivo, esperado", [
    (datetime(2026, 8, 1, 22, 0), time(23, 30), 90 * 60),      # más tarde hoy
    (datetime(2026, 8, 1, 23, 0), time(2, 0), 3 * 3600),       # ya pasó → mañana
    (datetime(2026, 8, 1, 12, 0), time(12, 0), 24 * 3600),     # misma hora → mañana
])
def test_segundos_hasta(ahora, objetivo, esperado):
    assert apagado.segundos_hasta(objetivo, ahora=ahora) == esperado


@pytest.mark.parametrize("delta, esperado", [
    (timedelta(minutes=45, seconds=10), "45 min 10 s"),
    (timedelta(hours=1, minutes=5), "1 h 05 min"),
    (timedelta(seconds=-30), "0 min 00 s"),   # ya vencido: nunca en negativo
])
def test_formatear_restante(delta, esperado):
    assert apagado.formatear_restante(delta) == esperado


# ─── programar ───────────────────────────────────────────────────────────────
def test_programar_apagado_usa_shutdown_con_retardo(shutdown):
    prog = apagado.programar("apagar", 900)
    assert _args(shutdown) == ["shutdown", "/s", "/t", "900"]
    assert prog.accion == "apagar"
    assert prog.restante() <= timedelta(seconds=900)


def test_programar_reinicio_forzado_agrega_flag(shutdown):
    apagado.programar("reiniciar", 60, forzar=True)
    assert _args(shutdown) == ["shutdown", "/r", "/t", "60", "/f"]


def test_accion_inmediata_no_lleva_temporizador(shutdown):
    apagado.programar("cerrar_sesion", 0)
    assert _args(shutdown) == ["shutdown", "/l"]


def test_accion_inmediata_con_retardo_es_error(shutdown):
    """Hibernar/cerrar sesión no admiten /t: mejor fallar que ejecutarlo YA."""
    with pytest.raises(apagado.ApagadoError, match="no admite temporizador"):
        apagado.programar("hibernar", 600)
    shutdown.assert_not_called()


@pytest.mark.parametrize("accion, segundos, patron", [
    ("volar", 60, "desconocida"),
    ("apagar", -1, "negativo"),
    ("apagar", apagado.MAX_SEGUNDOS + 1, "maximo"),
])
def test_programar_valida_antes_de_ejecutar(shutdown, accion, segundos, patron):
    with pytest.raises(apagado.ApagadoError, match=patron):
        apagado.programar(accion, segundos)
    shutdown.assert_not_called()


def test_error_de_shutdown_se_traduce(shutdown):
    shutdown.return_value.returncode = 1
    shutdown.return_value.stderr = "Acceso denegado".encode("cp850")
    with pytest.raises(apagado.ApagadoError, match="Acceso denegado"):
        apagado.programar("apagar", 60)


# ─── estado persistido ───────────────────────────────────────────────────────
def test_estado_recuerda_la_programacion(shutdown):
    assert apagado.estado() is None
    apagado.programar("apagar", 3600)
    prog = apagado.estado()
    assert prog is not None and prog.accion == "apagar"


def test_estado_ignora_una_programacion_vencida(shutdown):
    apagado.programar("apagar", 0)          # se cumple al instante
    assert apagado.estado() is None


def test_estado_tolera_un_archivo_corrupto(shutdown):
    apagado.ESTADO.parent.mkdir(parents=True, exist_ok=True)
    apagado.ESTADO.write_text("{no es json", encoding="utf-8")
    assert apagado.estado() is None


def test_cancelar_aborta_y_limpia_el_estado(shutdown):
    apagado.programar("apagar", 3600)
    apagado.cancelar()
    assert _args(shutdown) == ["shutdown", "/a"]
    assert apagado.estado() is None


def test_cancelar_limpia_el_estado_aunque_shutdown_falle(shutdown):
    """Si Windows dice que no había nada que abortar, el estado local igual se limpia."""
    apagado.programar("apagar", 3600)
    shutdown.return_value.returncode = 1
    with pytest.raises(apagado.ApagadoError):
        apagado.cancelar()
    assert apagado.estado() is None
