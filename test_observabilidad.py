"""
test_observabilidad.py — Que las métricas y los logs sigan sirviendo para vigilar.

Dos cosas que se rompen en silencio y solo se notan el día que hacen falta:

1. **`/metrics` abriéndose sin querer.** `django_prometheus.urls` registra la vista sin
   autenticación; aquí va envuelta en un bearer. Si alguien vuelve a incluir las urls de
   la librería, o toca `core/metrics.py`, estos tests lo cazan.
2. **El orden de los middlewares de Prometheus.** Tienen que envolver TODA la cadena. Si
   un middleware nuevo se cuela por fuera, las latencias dejan de medir la petición
   entera y nadie lo nota: el endpoint sigue devolviendo números, solo que mienten.

Se prueba en los dos sentidos: que el token válido entra y que la ausencia y el token
equivocado se rechazan.
"""

import json
import logging

import pytest
from django.test import Client

from core.logging import construir_logging

TOKEN = "token-de-prueba-para-metrics"


@pytest.fixture
def cliente_metrics(monkeypatch):
    """Cliente con METRICS_TOKEN configurado.

    El token vive en `core.conf` (pydantic-settings), no en los settings de Django, así
    que `override_settings` no sirve: se parchea el objeto que la vista consulta.
    """
    from core import metrics as modulo

    monkeypatch.setattr(modulo.env, "METRICS_TOKEN", TOKEN)
    return Client(headers={"host": "testserver"})


def test_metrics_sin_token_configurado_no_existe(monkeypatch):
    """Fallo seguro: sin `METRICS_TOKEN`, el endpoint es 404, no un endpoint abierto."""
    from core import metrics as modulo

    monkeypatch.setattr(modulo.env, "METRICS_TOKEN", "")
    assert Client().get("/metrics").status_code == 404
    # Ni siquiera con una cabecera: no hay token con el que acertar.
    assert Client().get("/metrics", headers={"authorization": "Bearer x"}).status_code == 404


def test_metrics_exige_bearer(cliente_metrics):
    """Sin cabecera y con el token equivocado, 401 (y se anuncia el esquema)."""
    r = cliente_metrics.get("/metrics")
    assert r.status_code == 401
    assert r["WWW-Authenticate"].startswith("Bearer")

    assert cliente_metrics.get("/metrics", headers={"authorization": "Bearer otro"}).status_code == 401
    # Sin el prefijo 'Bearer ' tampoco vale, aunque el token sea el bueno.
    assert cliente_metrics.get("/metrics", headers={"authorization": TOKEN}).status_code == 401


def test_metrics_con_token_expone_las_series_que_usan_las_alertas(cliente_metrics):
    """El otro sentido: con el token correcto responde, y trae lo que se vigila."""
    r = cliente_metrics.get("/metrics", headers={"authorization": f"Bearer {TOKEN}"})
    assert r.status_code == 200

    cuerpo = r.content.decode()
    # Las reglas de alerta (infra/observabilidad/alertas.yml) se construyen sobre esta
    # serie: si desaparece, las alertas dejan de dispararse sin dar ningún error.
    assert "django_http_responses_total_by_status_total" in cuerpo
    assert "django_http_requests_latency_seconds_by_view_method" in cuerpo


def test_los_middlewares_de_prometheus_envuelven_toda_la_cadena():
    """Before el primero y After el último, o las latencias miden de menos."""
    from django.conf import settings

    assert settings.MIDDLEWARE[0] == "django_prometheus.middleware.PrometheusBeforeMiddleware"
    assert settings.MIDDLEWARE[-1] == "django_prometheus.middleware.PrometheusAfterMiddleware"


def test_el_log_json_es_json_parseable_y_con_los_campos_renombrados(caplog):
    """Un log 'estructurado' que no parsea no sirve para filtrar por nivel ni por ruta."""
    config = construir_logging("json")
    formateador_conf = config["formatters"]["json"]
    assert formateador_conf["()"] == "pythonjsonlogger.json.JsonFormatter"

    # Se instancia el formateador tal y como lo haría dictConfig.
    from pythonjsonlogger.json import JsonFormatter

    formateador = JsonFormatter(
        fmt=formateador_conf["fmt"],
        rename_fields=formateador_conf["rename_fields"],
        static_fields=formateador_conf["static_fields"],
    )
    registro = logging.LogRecord(
        name="apps.liveops", level=logging.WARNING, pathname=__file__, lineno=1,
        msg="turno rechazado", args=(), exc_info=None,
    )
    datos = json.loads(formateador.format(registro))

    assert datos["level"] == "WARNING"          # renombrado desde levelname
    assert datos["name"] == "apps.liveops"
    assert datos["message"] == "turno rechazado"
    assert datos["service"] == "all-in-django"  # campo estático
    assert "timestamp" in datos                 # renombrado desde asctime


def test_el_formato_texto_sigue_siendo_el_de_siempre():
    """El toggle es explícito: pedir texto no debe colar JSON en la consola."""
    config = construir_logging("texto")
    assert config["root"]["handlers"] == ["console"]
    assert config["handlers"]["console"]["formatter"] == "verbose"
    # Y json es lo contrario, con el mismo cableado.
    assert construir_logging("json")["root"]["handlers"] == ["json"]


def test_django_request_se_registra_para_ver_los_5xx():
    """Sin este logger, un 500 solo existe en el traceback de gunicorn."""
    config = construir_logging("json")
    assert "django.request" in config["loggers"]
