"""
conftest.py — Garantiza variables de entorno mínimas para los tests.

pydantic-settings (core/conf.py) exige SECRET_KEY cuando DEBUG=False. En tests
fijamos valores seguros ANTES de que Django cargue la configuración, de modo que
la suite no dependa de un archivo `.env`.
"""

import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-prod")
os.environ.setdefault("DEBUG", "True")


def pytest_configure():
    """Fuerza SQLite en la suite salvo que DATABASE_URL venga del shell.

    `config.settings` ya construyó DATABASES leyendo `.env` (que puede apuntar a
    Postgres) porque `core.conf` se importa ANTES que este conftest; tocar os.environ
    aquí llegaría tarde. Por eso sobreescribimos DATABASES cuando Django ya está listo
    pero antes de que pytest-django cree la base de test. Para correr la suite contra
    Postgres, exporta DATABASE_URL en el shell antes de invocar pytest (el `.env` no
    cuenta: los tests deben ser rápidos y no depender de un servidor levantado).
    """
    if not os.environ.get("DATABASE_URL"):
        from django.conf import settings
        from django.db import connections

        # Mutar el dict existente (no reemplazarlo) para conservar las claves de
        # default que Django ya rellenó —ATOMIC_REQUESTS, AUTOCOMMIT, OPTIONS, TEST—;
        # un dict pelado rompía el manejo de transacciones (KeyError ATOMIC_REQUESTS).
        settings.DATABASES["default"].update(
            ENGINE="django.db.backends.sqlite3",
            NAME=str(settings.BASE_DIR / "db.sqlite3"),  # str: la creación de la test db concatena NAME
            HOST="", PORT="", USER="", PASSWORD="",
        )
        # Descartar el ConnectionHandler y los wrappers ya instanciados (eran de
        # Postgres): __init__ recrea el Local de conexiones para que la próxima se
        # cree con el backend SQLite; pop limpia la cached_property `settings`.
        connections.__dict__.pop("settings", None)
        connections.__init__()
