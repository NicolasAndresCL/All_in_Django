"""
main.py — Entrada de la UI NiceGUI de All in Django.

Cliente visual de la API REST (DRF): consume la API por HTTP (api_client.py), nunca el ORM.
Multipágina real (una ruta por vista, mismas URLs que tenía la UI Streamlit).

Config por entorno (se carga `nicegui_ui/.env` si existe, gitignored):
    API_BASE  → URL de la API (default http://localhost:8000/api)
    API_TOKEN → token DRF (la API exige autenticación)
    UI_PORT   → puerto de la UI (default 8501, el histórico de la UI)
    UI_HEADLESS=1 → no abrir navegador (contenedores)
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# La UI se importa CUALIFICADA (nicegui_ui.*) para no chocar en sys.modules con los
# módulos homónimos de streamlit_ui mientras conviven; para `python main.py` directo,
# la raíz del repo debe estar en sys.path.
_RAIZ = str(Path(__file__).resolve().parent.parent)
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

# .env local ANTES de importar vistas (get_client lee el token al instanciarse).
load_dotenv(Path(__file__).parent / ".env")

from nicegui import app, ui  # noqa: E402

from nicegui_ui.views import calendario, inicio, liveops, notas, tareas, tv  # noqa: E402

RUTAS = [
    ("/", inicio.render),
    ("/calendario", calendario.render),
    ("/liveops", liveops.render),
    ("/tareas", tareas.render),
    ("/notas", notas.render),
    ("/tv", tv.render),
]


def registrar_paginas() -> None:
    """Registra las 6 rutas. Función aparte porque el plugin de tests de NiceGUI
    resetea el registro de páginas entre tests (fixture autouse lo re-invoca)."""
    for ruta, fn in RUTAS:
        ui.page(ruta)(fn)


registrar_paginas()


if sys.platform == "win32":  # pragma: no cover - específico de Windows
    @app.on_startup
    async def _silenciar_desconexiones_windows() -> None:
        """En Windows + Python 3.14, cerrar la pestaña provoca ConnectionResetError
        ruidosos en el event loop de uvicorn; se silencian solo esos (patrón portado
        de taskflow-nicegui)."""
        import asyncio

        loop = asyncio.get_running_loop()
        handler_previo = loop.get_exception_handler()

        def handler(loop_, contexto):
            exc = contexto.get("exception")
            if isinstance(exc, (ConnectionResetError, asyncio.CancelledError)):
                return
            if handler_previo:
                handler_previo(loop_, contexto)
            else:
                loop_.default_exception_handler(contexto)

        loop.set_exception_handler(handler)


if __name__ in {"__main__", "__mp_main__"}:
    puerto = int(os.environ.get("UI_PORT", "8501"))
    ui.run(
        title="All in Django · UI",
        favicon="🗂️",
        port=puerto,
        dark=True,
        reload=False,
        show=os.environ.get("UI_HEADLESS", "") != "1",
    )
