"""Tests del módulo Registro de Tareas (modelo + API + resumen + dashboard)."""

from datetime import date, timedelta

import pytest
from rest_framework.test import APIClient

from .models import Registro
from .services import calcular_racha, calcular_resumen


def _reg(fecha, proyecto, tarea, horas):
    """Registro en memoria (sin guardar) para tests del cálculo puro."""
    return Registro(fecha=fecha, proyecto=proyecto, tarea=tarea,
                    duracion=timedelta(hours=horas))


@pytest.mark.django_db
def test_registro_horas_property():
    r = Registro.objects.create(fecha=date(2026, 6, 1), proyecto="P", tarea="T",
                                duracion=timedelta(hours=1, minutes=30))
    assert r.horas == 1.5


@pytest.mark.django_db
def test_api_crear_y_resumen():
    client = APIClient()
    client.post("/api/tareas/", {"fecha": "2026-06-01", "proyecto": "A", "tarea": "x",
                                 "duracion": "01:30:00"}, format="json")
    client.post("/api/tareas/", {"fecha": "2026-06-02", "proyecto": "A", "tarea": "y",
                                 "duracion": "00:30:00"}, format="json")
    client.post("/api/tareas/", {"fecha": "2026-06-02", "proyecto": "B", "tarea": "z",
                                 "duracion": "02:00:00"}, format="json")

    resumen = client.get("/api/tareas/resumen/")
    assert resumen.status_code == 200
    assert resumen.data["tareas"] == 3
    assert resumen.data["proyectos"] == 2
    assert resumen.data["horas_total"] == pytest.approx(4.0)
    por = {d["proyecto"]: d["horas"] for d in resumen.data["por_proyecto"]}
    assert por["A"] == pytest.approx(2.0) and por["B"] == pytest.approx(2.0)


@pytest.mark.django_db
def test_api_filtra_por_proyecto():
    Registro.objects.create(fecha=date(2026, 6, 1), proyecto="A", tarea="t", duracion=timedelta(hours=1))
    Registro.objects.create(fecha=date(2026, 6, 1), proyecto="B", tarea="t", duracion=timedelta(hours=1))
    resp = APIClient().get("/api/tareas/?proyecto=A")
    assert resp.data["count"] == 1


# ─── dashboard / racha (cálculo puro, sin BD) ────────────────────────────────
def test_calcular_racha():
    hoy = date(2026, 7, 2)
    # Tres días consecutivos terminando hoy.
    assert calcular_racha({date(2026, 7, 2), date(2026, 7, 1), date(2026, 6, 30)}, hoy) == 3
    # Cuenta desde ayer aunque no haya registro de hoy.
    assert calcular_racha({date(2026, 7, 1), date(2026, 6, 30)}, hoy) == 2
    # Racha rota: el más reciente es de hace 3 días.
    assert calcular_racha({date(2026, 6, 29)}, hoy) == 0
    assert calcular_racha(set(), hoy) == 0


def test_calcular_resumen_metricas_y_series():
    hoy = date(2026, 7, 2)
    regs = [
        _reg(date(2026, 7, 2), "A", "x", 2),
        _reg(date(2026, 7, 1), "A", "y", 1),
        _reg(date(2026, 7, 1), "B", "z", 3),
    ]
    res = calcular_resumen(regs, hoy)

    assert res["tareas"] == 3
    assert res["proyectos"] == 2
    assert res["horas_total"] == 6.0
    assert res["racha_dias"] == 2                 # 1 y 2 de julio consecutivos
    assert res["promedio_diario"] == 3.0          # 6 h / 2 días

    # Cada serie debe conservar el total de horas.
    assert sum(d["horas"] for d in res["por_proyecto"]) == 6.0
    assert sum(d["horas"] for d in res["por_dia"]) == 6.0
    assert sum(d["horas"] for d in res["por_semana"]) == 6.0
    assert sum(d["horas"] for d in res["por_tarea"]) == 6.0
    assert sum(d["horas"] for d in res["por_dia_semana"]) == 6.0

    # por_dia_semana siempre tiene los 7 días; por_dia agrupa por fecha.
    assert [d["dia"] for d in res["por_dia_semana"]][0] == "Lunes"
    assert len(res["por_dia_semana"]) == 7
    por_dia = {d["fecha"]: d["horas"] for d in res["por_dia"]}
    assert por_dia == {"2026-07-01": 4.0, "2026-07-02": 2.0}


@pytest.mark.django_db
def test_api_resumen_incluye_dashboard():
    Registro.objects.create(fecha=date(2026, 6, 1), proyecto="A", tarea="x",
                            duracion=timedelta(hours=2))
    data = APIClient().get("/api/tareas/resumen/").data
    # Claves nuevas del dashboard presentes.
    for clave in ("racha_dias", "promedio_diario", "promedio_semanal",
                  "por_tarea", "por_dia", "por_semana", "por_dia_semana"):
        assert clave in data
    assert len(data["por_dia_semana"]) == 7
