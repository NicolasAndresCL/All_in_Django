"""
Management command: importar_all_in_one

Lee las SQLite del proyecto Streamlit `all_in_one` y carga los datos en los modelos
Django. Idempotente: omite un modelo si ya tiene registros.

    python manage.py importar_all_in_one [--data RUTA] [--force]
"""

import sqlite3
from datetime import datetime, time
from pathlib import Path

import pandas as pd
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.calendario.models import Clase, TurnoPersonal
from apps.liveops.models import TurnoEquipo
from apps.notas.models import Nota
from apps.tareas.models import Registro
from core.conf import settings as env
from core.logging import get_logger

logger = get_logger(__name__)


def _fecha(s):
    return datetime.strptime(str(s)[:10], "%Y-%m-%d").date()


def _hora(s):
    """'HH:MM' → time; 'LIBRE'/vacío → None."""
    if not s or str(s).strip().upper() == "LIBRE":
        return None
    return datetime.strptime(str(s)[:5], "%H:%M").time()


def _dt_aware(s):
    """ISO (posiblemente naive) → datetime con zona, para USE_TZ=True."""
    dt = datetime.fromisoformat(str(s))
    return timezone.make_aware(dt) if timezone.is_naive(dt) else dt


def _filas(db_path: Path, tabla: str):
    """Lee todas las filas de `tabla` como dicts. [] si no existe."""
    if not db_path.exists():
        return []
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in con.execute(f"SELECT * FROM {tabla}")]
    except sqlite3.Error:
        return []
    finally:
        con.close()


class Command(BaseCommand):
    """Importa las SQLite de all_in_one a los modelos Django (idempotente sin --force)."""

    help = "Importa los datos de all_in_one (horarios.db, tareas.db, notas.db) a Django."

    def add_arguments(self, parser):
        parser.add_argument("--data", default=env.ALL_IN_ONE_DATA,
                            help="Carpeta data/ de all_in_one.")
        parser.add_argument("--force", action="store_true",
                            help="Importa aunque ya existan registros (puede duplicar).")

    @transaction.atomic
    def handle(self, *args, **opts):
        data = Path(opts["data"])
        force = opts["force"]
        horarios = data / "horarios.db"
        tareas = data / "tareas.db"
        notas = data / "notas.db"

        self.stdout.write(f"Importando desde: {data}")

        self._importar_clases(horarios, force)
        self._importar_turnos_personales(horarios, force)
        self._importar_turnos_equipo(horarios, force)
        self._importar_tareas(tareas, force)
        self._importar_notas(notas, force)

        self.stdout.write(self.style.SUCCESS("Importación finalizada."))

    # ── helpers por modelo ───────────────────────────────────────────────
    def _salta(self, modelo, force) -> bool:
        if not force and modelo.objects.exists():
            self.stdout.write(f"  [skip] {modelo.__name__}: ya tiene datos, se omite.")
            return True
        return False

    def _importar_clases(self, db, force):
        if self._salta(Clase, force):
            return
        n = 0
        for r in _filas(db, "clases"):
            Clase.objects.create(
                semana_inicio=_fecha(r["semana_inicio"]), dia=r["dia"],
                asignatura=r["asignatura"], entrada=_hora(r["entrada"]),
                salida=_hora(r["salida"]),
            )
            n += 1
        self.stdout.write(self.style.SUCCESS(f"  [OK]Clase: {n}"))

    def _importar_turnos_personales(self, db, force):
        if self._salta(TurnoPersonal, force):
            return
        n = 0
        for r in _filas(db, "turnos_personales"):
            TurnoPersonal.objects.create(
                semana_inicio=_fecha(r["semana_inicio"]), dia=r["dia"],
                entrada=_hora(r["entrada"]), salida=_hora(r["salida"]),
                es_libre=bool(r["es_libre"]),
            )
            n += 1
        self.stdout.write(self.style.SUCCESS(f"  [OK]TurnoPersonal: {n}"))

    def _importar_turnos_equipo(self, db, force):
        if self._salta(TurnoEquipo, force):
            return
        n = 0
        for r in _filas(db, "turnos_equipo"):
            TurnoEquipo.objects.create(
                semana_inicio=_fecha(r["semana_inicio"]), trabajador=r["trabajador"],
                dia=r["dia"], entrada=_hora(r["entrada"]), salida=_hora(r["salida"]),
                es_libre=bool(r["es_libre"]),
            )
            n += 1
        self.stdout.write(self.style.SUCCESS(f"  [OK]TurnoEquipo: {n}"))

    def _importar_tareas(self, db, force):
        if self._salta(Registro, force):
            return
        n = 0
        for r in _filas(db, "registro"):
            Registro.objects.create(
                fecha=_fecha(r["Fecha"]), proyecto=r["Proyecto"], tarea=r["Tarea"],
                duracion=pd.to_timedelta(r["Duracion"]).to_pytimedelta(),
            )
            n += 1
        self.stdout.write(self.style.SUCCESS(f"  [OK]Registro: {n}"))

    def _importar_notas(self, db, force):
        if self._salta(Nota, force):
            return
        n = 0
        for r in _filas(db, "notas"):
            nota = Nota.objects.create(
                titulo=r.get("titulo") or "", contenido=r.get("contenido") or "",
                formato=r.get("formato") or "md",
            )
            # Preserva las marcas de tiempo originales (update no dispara auto_now).
            if r.get("creado") and r.get("actualizado"):
                Nota.objects.filter(pk=nota.pk).update(
                    creado=_dt_aware(r["creado"]), actualizado=_dt_aware(r["actualizado"])
                )
            n += 1
        self.stdout.write(self.style.SUCCESS(f"  [OK]Nota: {n}"))
