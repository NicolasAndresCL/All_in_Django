"""Tests de la lógica pura de core (horarios + export). No requieren base de datos."""

from datetime import date, time

import pytest

from core import export, horarios


# ─── horarios ────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("fecha, esperado", [
    (date(2026, 6, 8), date(2026, 6, 8)),    # lunes
    (date(2026, 6, 14), date(2026, 6, 8)),   # domingo → lunes anterior
])
def test_get_semana_inicio(fecha, esperado):
    assert horarios.get_semana_inicio(fecha) == esperado


@pytest.mark.parametrize("h, esperado", [
    ("09:30", 9.5), ("00:00", 24.0), ("01:00", 25.0), ("LIBRE", None), ("", None),
])
def test_hora_a_decimal(h, esperado):
    res = horarios.hora_a_decimal(h)
    assert res is None if esperado is None else res == pytest.approx(esperado)


def test_turno_normal():
    assert horarios.calcular_horas_turno("Lunes", time(9, 0), time(15, 0)) == (6.0, 5.0, 0.0)


def test_turno_domingo_todo_extra():
    bruto, neto, extra = horarios.calcular_horas_turno("Domingo", time(9, 0), time(15, 0))
    assert (bruto, extra) == (6.0, 6.0)


def test_turno_cruza_medianoche():
    bruto, neto, _ = horarios.calcular_horas_turno("Lunes", time(18, 0), time(0, 0))
    assert (bruto, neto) == (6.0, 5.0)


def test_turno_sabado_trasnoche():
    _, _, extra = horarios.calcular_horas_turno("Sábado", time(22, 0), time(2, 0))
    assert extra == pytest.approx(2.0)


# ─── export ──────────────────────────────────────────────────────────────────
def test_generar_excel_firma():
    out = export.generar_excel(["a", "b"], [{"a": 1, "b": 2}])
    assert out[:4] == b"PK\x03\x04"


def test_generar_pdf_firma():
    out = export.generar_pdf("T", ["a"], [{"a": 1}])
    assert out.startswith(b"%PDF")
