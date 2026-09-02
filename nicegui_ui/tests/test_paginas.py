"""
Smoke tests de las páginas NiceGUI: cada ruta se abre con la API mockeada (responses)
y se verifica que el contenido clave se renderiza — equivalente al test_views_render.py
de la UI Streamlit (mismos fixtures de datos), ahora con nicegui.testing.User.

Aquí se comprueba que la página SE DIBUJA. Que los widgets HACEN algo al tocarlos está
en `test_interaccion.py`; los datos de ejemplo los comparten vía `datos_api.py`.
"""

from unittest.mock import patch

import responses
from datos_api import BASE, mock_api
from nicegui.testing import User

from nicegui_ui import apagado


# ─── una prueba por página ───────────────────────────────────────────────────
async def test_inicio(user: User) -> None:
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        mock_api(rsps)
        await user.open("/")
        await user.should_see("Conectado a la API")
        await user.should_see("Resumen")


async def test_calendario(user: User) -> None:
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        mock_api(rsps)
        await user.open("/calendario")
        await user.should_see("Clases (Santo Tomás)")
        await user.should_see("Guardar semana")


async def test_liveops(user: User) -> None:
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        mock_api(rsps)
        await user.open("/liveops")
        await user.should_see("Nuevo turno")
        await user.should_see("Importar / Exportar")


async def test_tareas(user: User) -> None:
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        mock_api(rsps)
        await user.open("/tareas")
        await user.should_see("Tareas Totales")
        await user.should_see("Nueva tarea")


async def test_notas(user: User) -> None:
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        mock_api(rsps)
        await user.open("/notas")
        await user.should_see("NotaUno")
        await user.should_see("Previsualización")


async def test_tv(user: User) -> None:
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        mock_api(rsps)
        await user.open("/tv")
        await user.should_see("TVN Chile")


async def test_apagado(user: User, monkeypatch) -> None:
    """La página se dibuja donde el apagado aplica (Windows). En CI corre en Linux,
    así que se simula la disponibilidad; shutdown.exe queda mockeado por si acaso."""
    monkeypatch.setattr(apagado, "disponible", lambda: True)
    with patch("nicegui_ui.apagado.subprocess.run"):
        await user.open("/apagado")
        await user.should_see("No hay ningun apagado programado")
        await user.should_see("Programar")


async def test_apagado_fuera_de_windows_avisa(user: User, monkeypatch) -> None:
    monkeypatch.setattr(apagado, "disponible", lambda: False)
    await user.open("/apagado")
    await user.should_see("solo esta disponible en Windows")


# ─── estados de error (la página avisa, no revienta) ─────────────────────────
async def test_inicio_explica_el_401_con_token_puesto(user: User) -> None:
    """Con token configurado (lo pone el conftest), un 401 apunta al token en sí —no a
    que falte—: suele ser un token de otra base de datos."""
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        rsps.get(f"{BASE}/", json={"detail": "no auth"}, status=401)
        await user.open("/")
        await user.should_see("rechaza el token")


async def test_inicio_no_culpa_al_token_de_un_rate_limit(user: User) -> None:
    """El fallo que motivó esto: recargar unas cuantas veces devolvía 429 y la UI lo
    anunciaba como credenciales inválidas, mandando a revisar donde no era."""
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        rsps.get(f"{BASE}/", json={"detail": "throttled"}, status=429)
        await user.open("/")
        await user.should_see("Límite de peticiones")


async def test_tv_error_api(user: User) -> None:
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        rsps.get(f"{BASE}/tv/canales/", json={"detail": "boom"}, status=503)
        await user.open("/tv")
        await user.should_see("No se pudieron obtener los canales")
