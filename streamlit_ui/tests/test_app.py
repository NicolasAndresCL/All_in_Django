"""Test de humo de app.py: la navegación se construye sin StreamlitAPIException.

Regresión: como todas las vistas exponen `render`, Streamlit infería el mismo
URL pathname y lanzaba "URL pathnames must be unique". Cada `st.Page` fija ahora
un `url_path` único; este test lo protege ejecutando el script de la app.
"""

from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def test_navegacion_sin_excepciones():
    # El conftest de este paquete añade streamlit_ui/ al sys.path, así que el
    # `from views import ...` de app.py resuelve igual que con `streamlit run`.
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception, [e.value for e in at.exception]
