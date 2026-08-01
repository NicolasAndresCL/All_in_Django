"""
apagado.py — Apagado/reinicio programado del PC (Windows) para la UI.

Es una utilidad **de escritorio local**, como el reloj y los logins: actúa sobre la
máquina donde corre la UI, NO sobre la API. Por eso no pasa por HTTP ni por el ORM;
envuelve `shutdown.exe`, que es quien mantiene el temporizador a nivel de sistema.

Que el temporizador lo lleve Windows (y no un hilo de Python) es deliberado: sobrevive
a que cierres la UI y se cancela con `shutdown /a` desde cualquier parte.

`shutdown.exe` solo acepta `/t` (retardo) con apagar y reiniciar; hibernar y cerrar
sesión son inmediatos y no se pueden abortar. Esa diferencia se refleja en `ACCIONES`.

Los `datetime` de este módulo son **naive a propósito** (ruff DTZ): "apagar a las 23:30"
es hora local de pared del equipo, que es justo lo que `shutdown.exe` entiende.
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, time, timedelta
from pathlib import Path

# Retardo máximo admitido (7 días). `shutdown.exe` acepta mucho más, pero un plazo
# tan largo casi siempre es un dedazo del usuario.
MAX_SEGUNDOS = 7 * 24 * 3600

# Dónde se recuerda la programación vigente, para que la UI pueda mostrar la cuenta
# atrás aunque se recargue la página o se reinicie el proceso.
ESTADO = Path.home() / ".all_in_django" / "apagado.json"


class ApagadoError(RuntimeError):
    """Falló la programación/cancelación del apagado.

    No hereda de `core.exceptions.AllInDjangoError` a propósito: la UI es un cliente
    autónomo (su imagen solo copia `nicegui_ui/`) y no importa el paquete del backend.
    """


@dataclass(frozen=True)
class Accion:
    flag: str            # bandera de shutdown.exe
    etiqueta: str        # texto para la UI
    programable: bool    # admite /t (y por tanto cancelación con /a)


ACCIONES: dict[str, Accion] = {
    "apagar": Accion("/s", "Apagar", True),
    "reiniciar": Accion("/r", "Reiniciar", True),
    "hibernar": Accion("/h", "Hibernar (inmediato)", False),
    "cerrar_sesion": Accion("/l", "Cerrar sesion (inmediato)", False),
}

# Atajos que ofrece la UI, en minutos.
PRESETS = [15, 30, 60, 90, 120, 240]


@dataclass(frozen=True)
class Programacion:
    """Apagado vigente: qué acción y para cuándo."""

    accion: str
    momento: str  # ISO 8601

    @property
    def cuando(self) -> datetime:
        return datetime.fromisoformat(self.momento)

    def restante(self, ahora: datetime | None = None) -> timedelta:
        return self.cuando - (ahora or datetime.now())


def disponible() -> bool:
    """El apagado programado solo tiene sentido en la máquina Windows del usuario
    (dentro de un contenedor apagaría el contenedor, no el PC)."""
    return sys.platform == "win32"


def segundos_hasta(objetivo: time, ahora: datetime | None = None) -> int:
    """Segundos desde `ahora` hasta la próxima ocurrencia de la hora `objetivo`.

    Si la hora ya pasó hoy, se entiende que es la de mañana (programar "a las 02:00"
    a las 23:00 debe apuntar a la madrugada siguiente, no al pasado).
    """
    ahora = ahora or datetime.now()
    cuando = datetime.combine(ahora.date(), objetivo)
    if cuando <= ahora:
        cuando += timedelta(days=1)
    return int((cuando - ahora).total_seconds())


def _ejecutar(args: list[str]) -> None:
    """Invoca shutdown.exe y traduce el fallo a ApagadoError con su mensaje real."""
    try:
        # check=False: el returncode se traduce abajo a ApagadoError con el mensaje real.
        proc = subprocess.run(["shutdown", *args], capture_output=True, check=False)
    except OSError as exc:  # pragma: no cover - shutdown.exe siempre existe en Windows
        raise ApagadoError(f"No se pudo invocar shutdown.exe: {exc}") from exc
    if proc.returncode != 0:
        # La consola de Windows responde en la codificación OEM, no en UTF-8.
        detalle = (proc.stderr or proc.stdout).decode("cp850", errors="replace").strip()
        raise ApagadoError(detalle or f"shutdown.exe devolvio {proc.returncode}")


def _guardar(prog: Programacion | None) -> None:
    if prog is None:
        ESTADO.unlink(missing_ok=True)
        return
    ESTADO.parent.mkdir(parents=True, exist_ok=True)
    ESTADO.write_text(json.dumps(asdict(prog)), encoding="utf-8")


def estado() -> Programacion | None:
    """Programación vigente, o None si no hay (o si ya pasó su hora)."""
    try:
        prog = Programacion(**json.loads(ESTADO.read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError):
        return None
    return prog if prog.restante() > timedelta(0) else None


def programar(accion: str, segundos: int, forzar: bool = False) -> Programacion:
    """Programa `accion` dentro de `segundos`. Devuelve la programación registrada.

    `forzar` (/f) cierra las aplicaciones sin esperar a que guarden: útil si algo
    bloquea el apagado, peligroso si tienes trabajo sin guardar.
    """
    if accion not in ACCIONES:
        raise ApagadoError(f"Accion desconocida: {accion}")
    cfg = ACCIONES[accion]
    if segundos < 0:
        raise ApagadoError("El retardo no puede ser negativo.")
    if segundos > MAX_SEGUNDOS:
        raise ApagadoError(f"El retardo maximo es de {MAX_SEGUNDOS // 3600} horas.")
    if segundos and not cfg.programable:
        raise ApagadoError(f"'{cfg.etiqueta}' no admite temporizador; es inmediato.")

    args = [cfg.flag]
    if cfg.programable:
        args += ["/t", str(segundos)]
    if forzar:
        args.append("/f")
    _ejecutar(args)

    prog = Programacion(accion, (datetime.now() + timedelta(seconds=segundos)).isoformat())
    if cfg.programable:
        _guardar(prog)
    return prog


def cancelar() -> None:
    """Aborta el apagado programado (`shutdown /a`). Idempotente para la UI: si no
    había nada programado, Windows falla y lo traducimos a un mensaje claro."""
    try:
        _ejecutar(["/a"])
    finally:
        _guardar(None)


def formatear_restante(delta: timedelta) -> str:
    """'1 h 05 min' / '45 min 10 s' — cuenta atrás legible para la UI."""
    total = max(0, int(delta.total_seconds()))
    h, resto = divmod(total, 3600)
    m, s = divmod(resto, 60)
    return f"{h} h {m:02d} min" if h else f"{m} min {s:02d} s"
