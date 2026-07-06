"""
Tests del endurecimiento: autenticación por token, throttling y settings seguros.

La API exige IsAuthenticated (token o sesión); /healthz/ y la vista web de inicio
quedan públicos (no son DRF). El endpoint /api/token/ tiene rate limit propio
(scope "token") para frenar fuerza bruta.
"""

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from core.conf import Settings


# ─── autenticación ───────────────────────────────────────────────────────────
@pytest.mark.django_db
@pytest.mark.parametrize("ruta", [
    "/api/clases/", "/api/turnos-personales/", "/api/turnos-equipo/",
    "/api/tareas/", "/api/notas/", "/api/tareas/resumen/", "/api/tv/canales/",
])
def test_api_sin_token_da_401(ruta):
    cache.clear()  # aísla el contador de throttle anónimo
    resp = APIClient().get(ruta)
    assert resp.status_code == 401


@pytest.mark.django_db
def test_healthz_e_inicio_siguen_publicos(client):
    # No son endpoints DRF: el healthcheck de Compose/K8s y el panel web no requieren token.
    assert client.get("/healthz/").status_code == 200
    assert client.get("/").status_code == 200


@pytest.mark.django_db
def test_obtener_token_y_usarlo(usuario):
    cache.clear()
    anon = APIClient()
    resp = anon.post("/api/token/", {"username": "tester", "password": "tester-pass-123"},
                     format="json")
    assert resp.status_code == 200
    token = resp.data["token"]

    con_token = APIClient()
    con_token.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    assert con_token.get("/api/clases/").status_code == 200


@pytest.mark.django_db
def test_token_con_credenciales_malas_da_400(usuario):
    cache.clear()
    resp = APIClient().post("/api/token/", {"username": "tester", "password": "nop"},
                            format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_api_autenticado_responde(api):
    assert api.get("/api/clases/").status_code == 200


# ─── throttling ──────────────────────────────────────────────────────────────
@pytest.mark.django_db
def test_token_endpoint_tiene_rate_limit(usuario, settings):
    """El scope 'token' corta tras N intentos (default 10/min): la N+1 devuelve 429."""
    cache.clear()
    anon = APIClient()
    limite = int(settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["token"].split("/")[0])
    for _ in range(limite):
        r = anon.post("/api/token/", {"username": "tester", "password": "nop"}, format="json")
        assert r.status_code == 400  # rechazado por credenciales, no por rate
    r = anon.post("/api/token/", {"username": "tester", "password": "nop"}, format="json")
    assert r.status_code == 429


def test_throttle_rates_configurados(settings):
    rates = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
    assert set(rates) == {"anon", "user", "token"}
    assert all(rates.values())


# ─── settings de seguridad (pydantic) ────────────────────────────────────────
def test_secret_key_debil_falla_con_debug_false():
    with pytest.raises(ValueError, match="débil"):
        Settings(SECRET_KEY="corta123", DEBUG=False, _env_file=None)


def test_secret_key_fuerte_pasa_con_debug_false():
    s = Settings(SECRET_KEY="x" * 30 + "abcdefghij" + "9" * 15, DEBUG=False, _env_file=None)
    assert not s.DEBUG


def test_secure_https_es_toggle_explicito():
    # Off por defecto (Compose sirve HTTP plano con DEBUG=False); on solo tras TLS real.
    clave = "abcdefghij-0123456789" * 3  # >= 50 chars y >= 5 distintos
    assert Settings(SECRET_KEY=clave, DEBUG=False, _env_file=None).SECURE_HTTPS is False
    assert Settings(SECRET_KEY=clave, DEBUG=False, SECURE_HTTPS=True,
                    _env_file=None).SECURE_HTTPS is True
