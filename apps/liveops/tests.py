"""Tests del módulo LiveOps (servicios de importación + modelo + API importar)."""

from datetime import time

import pandas as pd
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from . import services
from .models import TurnoEquipo


# ─── servicios ───────────────────────────────────────────────────────────────
@pytest.mark.parametrize("entrada, esperado", [
    ("Barbara Vilches", "Babi"), ("BV", "Babi"), ("Nicolás Cano", "Nico"),
    ("Manuel Meza", "Manu"), ("Jorge", "Jorge"), ("Desconocido", "Desconocido"),
])
def test_normalizar_trabajador(entrada, esperado):
    assert services.normalizar_trabajador(entrada) == esperado


@pytest.mark.parametrize("valor, esperado", [
    ("13:00", time(13, 0)), ("9:00", time(9, 0)), ("—", None), ("LIBRE", None), (None, None),
])
def test_parse_hora(valor, esperado):
    assert services.parse_hora(valor) == esperado


def test_preparar_turnos_equipo():
    df = pd.DataFrame({
        "Fecha": ["2026-06-01", "2026-06-01"],
        "Agente": ["Barbara Vilches", "Manuel Meza"],
        "Entrada": ["13:00", "—"], "Salida": ["22:00", "—"], "Estado": ["Turno", "Libre"],
    })
    filas, resumen, errores = services.preparar_turnos_equipo(df)
    assert errores == []
    assert resumen["agentes"] == ["Babi", "Manu"]
    babi = next(f for f in filas if f["trabajador"] == "Babi")
    assert babi["dia"] == "Lunes" and babi["entrada"] == time(13, 0) and not babi["es_libre"]
    manu = next(f for f in filas if f["trabajador"] == "Manu")
    assert manu["es_libre"] and manu["entrada"] is None


# ─── modelo + guardar ────────────────────────────────────────────────────────
@pytest.mark.django_db
def test_guardar_turnos_calcula_y_no_duplica():
    from datetime import date
    fila = {"semana_inicio": date(2026, 6, 1), "trabajador": "Babi", "dia": "Lunes",
            "entrada": time(13, 0), "salida": time(22, 0), "es_libre": False}  # bruto 9
    services.guardar_turnos([fila])
    # Actualizar a un turno de 3h (10–13): bruto/neto deben RECALCULARSE al actualizar.
    # (Regresión: update_or_create pasaba update_fields y no persistía bruto/neto.)
    services.guardar_turnos([{**fila, "entrada": time(10, 0), "salida": time(13, 0)}])
    qs = TurnoEquipo.objects.filter(semana_inicio=date(2026, 6, 1), trabajador="Babi", dia="Lunes")
    assert qs.count() == 1                 # upsert: no duplica
    t = qs.first()
    assert t.entrada == time(10, 0) and t.bruto == 3.0 and t.neto == 2.0


@pytest.mark.django_db
def test_api_reescribir_turno_equipo_reemplaza():
    client = APIClient()
    base = {"semana_inicio": "2026-06-01", "trabajador": "Nico", "dia": "Lunes"}
    r1 = client.post("/api/turnos-equipo/", {**base, "entrada": "09:00:00", "salida": "18:00:00"},
                     format="json")
    assert r1.status_code == 201
    # Reescribir el mismo (semana, trabajador, día): reemplaza, no da 400.
    r2 = client.post("/api/turnos-equipo/", {**base, "entrada": "13:00:00", "salida": "22:00:00"},
                     format="json")
    assert r2.status_code == 201, r2.data
    qs = TurnoEquipo.objects.filter(semana_inicio="2026-06-01", trabajador="Nico", dia="Lunes")
    assert qs.count() == 1 and qs.get().entrada == time(13, 0)


# ─── API importar ────────────────────────────────────────────────────────────
@pytest.mark.django_db
def test_api_importar_csv():
    csv = b"Fecha,Agente,Entrada,Salida\n2026-06-01,Barbara Vilches,13:00,22:00\n"
    archivo = SimpleUploadedFile("turnos.csv", csv, content_type="text/csv")
    resp = APIClient().post("/api/turnos-equipo/importar/", {"archivo": archivo}, format="multipart")
    assert resp.status_code == 201
    assert resp.data["importadas"] == 1
    assert TurnoEquipo.objects.count() == 1


@pytest.mark.django_db
def test_api_importar_sin_archivo_da_400():
    resp = APIClient().post("/api/turnos-equipo/importar/", {}, format="multipart")
    assert resp.status_code == 400


# ─── imprimir (PDF con formato) ──────────────────────────────────────────────
@pytest.mark.django_db
def test_api_imprimir_equipo():
    from datetime import date
    TurnoEquipo.objects.create(semana_inicio=date(2026, 6, 1), trabajador="Babi",
                               dia="Lunes", entrada=time(13, 0), salida=time(22, 0))
    resp = APIClient().get("/api/turnos-equipo/imprimir/?semana_inicio=2026-06-01")
    assert resp.status_code == 200
    assert resp["Content-Type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF")
