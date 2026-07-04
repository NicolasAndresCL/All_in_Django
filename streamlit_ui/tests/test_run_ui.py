"""Tests de run_ui: selección de puerto y arranque/reutilización de la API."""

import socket

import pytest

import run_ui


def test_puerto_libre_detecta_ocupado():
    # Abre un puerto efímero y comprueba que se detecta como ocupado.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.listen()
        puerto = s.getsockname()[1]
        assert run_ui.puerto_libre(puerto) is False
    # Tras cerrarlo, vuelve a estar libre.
    assert run_ui.puerto_libre(puerto) is True


def test_encontrar_puerto_salta_el_ocupado():
    # Ocupa un puerto base y verifica que encontrar_puerto elige el siguiente.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.listen()
        base = s.getsockname()[1]
        elegido = run_ui.encontrar_puerto(base)
        assert elegido > base
        assert run_ui.puerto_libre(elegido) is True


def test_encontrar_puerto_devuelve_base_si_libre():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        base = s.getsockname()[1]
    # Cerrado el socket, `base` está libre → se devuelve tal cual.
    assert run_ui.encontrar_puerto(base) == base


# ─── API ──────────────────────────────────────────────────────────────────────
class _FakeResp:
    def __init__(self, status):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_api_responde_true(monkeypatch):
    monkeypatch.setattr(run_ui.urllib.request, "urlopen", lambda *a, **k: _FakeResp(200))
    assert run_ui.api_responde("http://x/api/") is True


def test_api_responde_false_si_excepcion(monkeypatch):
    def boom(*a, **k):
        raise OSError("conexion rechazada")

    monkeypatch.setattr(run_ui.urllib.request, "urlopen", boom)
    assert run_ui.api_responde("http://x/api/") is False


def test_arrancar_api_reutiliza_si_ya_responde(monkeypatch):
    """Si la API ya contesta, no se lanza otro proceso (devuelve None)."""
    monkeypatch.setattr(run_ui, "api_responde", lambda *a, **k: True)

    def no_deberia(*a, **k):
        raise AssertionError("no debe arrancar un proceso si la API ya responde")

    monkeypatch.setattr(run_ui.subprocess, "Popen", no_deberia)
    monkeypatch.setattr(run_ui.subprocess, "run", no_deberia)
    assert run_ui.arrancar_api() is None


def test_esperar_api_agota_intentos(monkeypatch):
    monkeypatch.setattr(run_ui, "api_responde", lambda *a, **k: False)
    monkeypatch.setattr(run_ui.time, "sleep", lambda *_: None)  # sin esperas reales
    assert run_ui.esperar_api("http://x/api/", intentos=3, espera=0) is False
