"""Tests del módulo Calendario (modelos + API + imprimir + copiar semana)."""

from datetime import date, time

import pytest
from rest_framework.test import APIClient

from .models import Clase, TurnoPersonal
from .services import copiar_clases, copiar_turnos_personales


@pytest.mark.django_db
def test_clase_calcula_horas_al_guardar():
    c = Clase.objects.create(
        semana_inicio=date(2026, 6, 8), dia="Lunes", asignatura="Anatomía",
        entrada=time(8, 30), salida=time(10, 0),
    )
    assert c.horas == 1.5


@pytest.mark.django_db
def test_turno_personal_calcula_bruto_neto_extra():
    t = TurnoPersonal.objects.create(
        semana_inicio=date(2026, 6, 8), dia="Lunes", entrada=time(9, 0), salida=time(15, 0),
    )
    assert (t.bruto, t.neto, t.extra, t.es_libre) == (6.0, 5.0, 0.0, False)


@pytest.mark.django_db
def test_turno_personal_libre():
    t = TurnoPersonal.objects.create(semana_inicio=date(2026, 6, 8), dia="Martes", es_libre=True)
    assert t.es_libre and t.entrada is None and t.bruto == 0


@pytest.mark.django_db
def test_api_crear_y_listar_clase():
    client = APIClient()
    resp = client.post("/api/clases/", {
        "semana_inicio": "2026-06-08", "dia": "Lunes", "asignatura": "Mate",
        "entrada": "08:30:00", "salida": "10:00:00",
    }, format="json")
    assert resp.status_code == 201
    assert resp.data["horas"] == 1.5

    lista = client.get("/api/clases/?semana_inicio=2026-06-08")
    assert lista.status_code == 200
    assert lista.data["count"] == 1


@pytest.mark.django_db
def test_api_exportar_excel():
    Clase.objects.create(semana_inicio=date(2026, 6, 8), dia="Lunes",
                         asignatura="Mate", entrada=time(8, 30), salida=time(10, 0))
    resp = APIClient().get("/api/clases/exportar/?formato=excel")
    assert resp.status_code == 200
    assert resp["Content-Type"].startswith("application/vnd.openxmlformats")


# ─── imprimir (PDF con formato) ──────────────────────────────────────────────
@pytest.mark.django_db
def test_api_imprimir_estudio():
    Clase.objects.create(semana_inicio=date(2026, 6, 8), dia="Lunes",
                         asignatura="Anatomía", entrada=time(8, 30), salida=time(10, 0))
    resp = APIClient().get("/api/clases/imprimir/?semana_inicio=2026-06-08")
    assert resp.status_code == 200
    assert resp["Content-Type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF")


@pytest.mark.django_db
def test_api_imprimir_laboral():
    TurnoPersonal.objects.create(semana_inicio=date(2026, 6, 8), dia="Lunes",
                                 entrada=time(18, 0), salida=time(23, 0))
    resp = APIClient().get("/api/turnos-personales/imprimir/?semana_inicio=2026-06-08")
    assert resp.status_code == 200
    assert resp.content.startswith(b"%PDF")


@pytest.mark.django_db
def test_api_imprimir_maestro_combina_estudio_y_trabajo():
    Clase.objects.create(semana_inicio=date(2026, 6, 8), dia="Lunes",
                         asignatura="Mate", entrada=time(8, 0), salida=time(10, 0))
    TurnoPersonal.objects.create(semana_inicio=date(2026, 6, 8), dia="Lunes",
                                 entrada=time(18, 0), salida=time(23, 0))
    resp = APIClient().get("/api/clases/imprimir_maestro/?semana_inicio=2026-06-08")
    assert resp.status_code == 200
    assert resp.content.startswith(b"%PDF")


# ─── copiar semana ───────────────────────────────────────────────────────────
@pytest.mark.django_db
def test_copiar_clases_reemplaza_destino():
    Clase.objects.create(semana_inicio=date(2026, 6, 1), dia="Lunes",
                         asignatura="Origen", entrada=time(8, 0), salida=time(9, 0))
    # La semana destino ya tenía una clase distinta que debe desaparecer.
    Clase.objects.create(semana_inicio=date(2026, 6, 8), dia="Martes",
                         asignatura="Vieja", entrada=time(8, 0), salida=time(9, 0))
    n = copiar_clases(date(2026, 6, 1), date(2026, 6, 8))
    assert n == 1
    destino = Clase.objects.filter(semana_inicio=date(2026, 6, 8))
    assert destino.count() == 1
    assert destino.get().asignatura == "Origen"


@pytest.mark.django_db
def test_copiar_turnos_recalcula_en_destino():
    TurnoPersonal.objects.create(semana_inicio=date(2026, 6, 1), dia="Lunes",
                                 entrada=time(18, 0), salida=time(23, 0))
    n = copiar_turnos_personales(date(2026, 6, 1), date(2026, 6, 8))
    assert n == 1
    t = TurnoPersonal.objects.get(semana_inicio=date(2026, 6, 8))
    assert t.entrada == time(18, 0) and t.bruto == 5.0  # recalculado en save()


@pytest.mark.django_db
def test_api_copiar_semana_clases():
    Clase.objects.create(semana_inicio=date(2026, 6, 1), dia="Lunes",
                         asignatura="X", entrada=time(8, 0), salida=time(9, 0))
    resp = APIClient().post("/api/clases/copiar_semana/",
                            {"origen": "2026-06-01", "destino": "2026-06-08"}, format="json")
    assert resp.status_code == 201
    assert resp.data["copiadas"] == 1
    assert Clase.objects.filter(semana_inicio=date(2026, 6, 8)).count() == 1


@pytest.mark.django_db
def test_api_copiar_semana_sin_datos_da_400():
    resp = APIClient().post("/api/clases/copiar_semana/", {"origen": "2026-06-01"}, format="json")
    assert resp.status_code == 400
