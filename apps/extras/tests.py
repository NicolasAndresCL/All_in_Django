"""Tests del módulo Extras: importador `importar_all_in_one` y vista web `inicio`."""

import sqlite3
from datetime import date, time

import pytest
from django.core.management import call_command
from django.test import Client

from apps.calendario.models import Clase, TurnoPersonal
from apps.liveops.models import TurnoEquipo
from apps.notas.models import Nota
from apps.tareas.models import Registro


def _crear_dbs(carpeta):
    """Crea horarios.db, tareas.db y notas.db de all_in_one con una fila cada tabla."""
    horarios = sqlite3.connect(str(carpeta / "horarios.db"))
    horarios.execute(
        "CREATE TABLE clases (semana_inicio TEXT, dia TEXT, asignatura TEXT, "
        "entrada TEXT, salida TEXT)"
    )
    horarios.execute(
        "INSERT INTO clases VALUES ('2026-06-08','Lunes','Anatomía','08:30','10:00')"
    )
    horarios.execute(
        "CREATE TABLE turnos_personales (semana_inicio TEXT, dia TEXT, entrada TEXT, "
        "salida TEXT, es_libre INTEGER)"
    )
    horarios.execute(
        "INSERT INTO turnos_personales VALUES ('2026-06-08','Lunes','18:00','23:00',0)"
    )
    horarios.execute(
        "CREATE TABLE turnos_equipo (semana_inicio TEXT, trabajador TEXT, dia TEXT, "
        "entrada TEXT, salida TEXT, es_libre INTEGER)"
    )
    horarios.execute(
        "INSERT INTO turnos_equipo VALUES ('2026-06-08','Babi','Lunes','13:00','22:00',0)"
    )
    horarios.commit()
    horarios.close()

    tareas = sqlite3.connect(str(carpeta / "tareas.db"))
    tareas.execute("CREATE TABLE registro (Fecha TEXT, Proyecto TEXT, Tarea TEXT, Duracion TEXT)")
    tareas.execute("INSERT INTO registro VALUES ('2026-06-01','A','tarea x','01:30:00')")
    tareas.commit()
    tareas.close()

    notas = sqlite3.connect(str(carpeta / "notas.db"))
    notas.execute(
        "CREATE TABLE notas (titulo TEXT, contenido TEXT, formato TEXT, "
        "creado TEXT, actualizado TEXT)"
    )
    notas.execute(
        "INSERT INTO notas VALUES ('N1','# Hola','md','2026-06-01T10:00:00','2026-06-02T11:00:00')"
    )
    notas.commit()
    notas.close()


@pytest.mark.django_db
def test_importar_carga_todos_los_modelos(tmp_path):
    _crear_dbs(tmp_path)
    call_command("importar_all_in_one", data=str(tmp_path))

    clase = Clase.objects.get()
    assert clase.asignatura == "Anatomía" and clase.horas == 1.5

    turno_p = TurnoPersonal.objects.get()
    assert turno_p.dia == "Lunes" and turno_p.entrada == time(18, 0) and not turno_p.es_libre

    turno_e = TurnoEquipo.objects.get()
    assert turno_e.trabajador == "Babi" and turno_e.bruto == 9.0

    reg = Registro.objects.get()
    assert reg.proyecto == "A" and reg.horas == 1.5

    nota = Nota.objects.get()
    # Se preservan las marcas de tiempo originales del all_in_one.
    assert nota.titulo == "N1" and nota.creado.date() == date(2026, 6, 1)


@pytest.mark.django_db
def test_importar_es_idempotente(tmp_path):
    """Sin --force, un modelo con datos previos se omite (no duplica)."""
    _crear_dbs(tmp_path)
    Clase.objects.create(
        semana_inicio=date(2026, 1, 1), dia="Lunes", asignatura="Previa",
        entrada=time(9, 0), salida=time(10, 0),
    )
    call_command("importar_all_in_one", data=str(tmp_path))
    # La clase previa sigue siendo la única (se omitió la importación de Clase).
    assert Clase.objects.count() == 1
    assert Clase.objects.get().asignatura == "Previa"


@pytest.mark.django_db
def test_importar_carpeta_inexistente_no_falla(tmp_path):
    """Si faltan las DBs, el command corre sin crear nada ni lanzar error."""
    call_command("importar_all_in_one", data=str(tmp_path / "no_existe"))
    assert Clase.objects.count() == 0


@pytest.mark.django_db
def test_vista_inicio_responde(client: Client):
    Clase.objects.create(
        semana_inicio=date(2026, 6, 8), dia="Lunes", asignatura="Mate",
        entrada=time(8, 0), salida=time(10, 0),
    )
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Horas" in resp.content  # las métricas se renderizan en el template
