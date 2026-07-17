"""
conftest de los tests de la UI NiceGUI.

- API_BASE/API_TOKEN se fijan por test (autouse, con restore) para no contaminar el
  entorno de las suites vecinas (p. ej. el test "sin token" del api_client de
  streamlit_ui, que lee el mismo os.environ). `get_client()` cachea el cliente
  (lru_cache) en el primer uso, y `load_dotenv` de main.py no pisa lo ya definido.
- La fixture `user` (plugin `nicegui.testing.user_plugin`, activado en el conftest
  RAÍZ: pytest exige declararlo top-level) ejecuta `nicegui_ui/main.py` (opción
  `main_file` de pytest.ini) en un contexto simulado por cada test.
- Los módulos se importan CUALIFICADOS (`nicegui_ui.api_client`, ...) para no chocar
  en sys.modules con los homónimos de streamlit_ui mientras ambas UIs convivan.
"""

import os

import pytest


@pytest.fixture(autouse=True)
def _entorno_api():
    """Entorno de la API para estos tests, restaurado al salir de cada uno."""
    anterior = {k: os.environ.get(k) for k in ("API_BASE", "API_TOKEN")}
    os.environ["API_BASE"] = "http://testserver/api"
    os.environ.setdefault("API_TOKEN", "token-de-test")
    yield
    for clave, valor in anterior.items():
        if valor is None:
            os.environ.pop(clave, None)
        else:
            os.environ[clave] = valor
