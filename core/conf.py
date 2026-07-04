"""
core/conf.py — Configuración tipada y validada con pydantic-settings.

Alternativa moderna a python-dotenv: además de leer `.env`, valida tipos y falla
con un mensaje claro si algo crítico está mal (p. ej. SECRET_KEY sin configurar en
producción). `config/settings.py` consume la instancia `settings` de aquí.
"""

from pathlib import Path
from typing import Annotated

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent

# Valor centinela: si sigue así con DEBUG=False, es un despliegue inseguro.
_SECRET_INSEGURA = "dev-insecure-change-me"


class Settings(BaseSettings):
    """Configuración de la aplicación leída del entorno / `.env`."""

    SECRET_KEY: str = _SECRET_INSEGURA
    DEBUG: bool = False
    # NoDecode: pydantic-settings NO intenta parsear JSON; el validador de abajo
    # acepta lista o cadena separada por comas.
    ALLOWED_HOSTS: Annotated[list[str], NoDecode] = ["127.0.0.1", "localhost"]

    # Base de datos: si se define, `config.settings` la parsea con dj-database-url
    # (p. ej. postgres://user:pass@localhost:5432/all_in_django). Vacía/None → SQLite local.
    DATABASE_URL: str | None = None

    # Credenciales de los logins automáticos (management command login_menu).
    CISCO_USER: str = ""
    CISCO_PASS: str = ""
    SENCE_RUT: str = ""
    CLAVE_UNICA: str = ""

    # Carpeta con las SQLite de all_in_one para el comando de importación.
    ALL_IN_ONE_DATA: str = str(BASE_DIR.parent / "all_in_one" / "data")

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("ALLOWED_HOSTS", mode="before")
    @classmethod
    def _split_hosts(cls, v):
        """Acepta lista JSON o cadena separada por comas en el .env."""
        if isinstance(v, str) and not v.strip().startswith("["):
            return [h.strip() for h in v.split(",") if h.strip()]
        return v

    @model_validator(mode="after")
    def _validar_seguridad(self):
        if not self.DEBUG and self.SECRET_KEY == _SECRET_INSEGURA:
            raise ValueError(
                "SECRET_KEY no configurada. Define SECRET_KEY en .env antes de "
                "ejecutar con DEBUG=False."
            )
        return self


# Instancia única, validada al importar el módulo.
settings = Settings()
