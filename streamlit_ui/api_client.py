"""
api_client.py — Cliente HTTP centralizado para la API REST de All in Django.

La UI de Streamlit NO toca el ORM ni la base de datos: es un cliente desacoplado
que habla con la API DRF por HTTP (mismo patrón que consumir la API desde fuera).
Toda la lógica de red vive aquí; las vistas solo llaman a estos métodos.

La URL base se toma de `st.secrets["API_BASE"]`, de la variable de entorno
`API_BASE` o, por defecto, `http://localhost:8000/api`.
"""

from __future__ import annotations

import os
from typing import Any

import requests
import streamlit as st


def _base_url() -> str:
    """Resuelve la URL base de la API (secrets > entorno > localhost)."""
    try:
        if "API_BASE" in st.secrets:  # type: ignore[operator]
            return str(st.secrets["API_BASE"]).rstrip("/")
    except Exception:
        pass
    return os.environ.get("API_BASE", "http://localhost:8000/api").rstrip("/")


class APIError(RuntimeError):
    """Error de la API con el detalle que devolvió el backend (si lo hay)."""

    def __init__(self, mensaje: str, status: int | None = None, detalle: Any = None):
        super().__init__(mensaje)
        self.status = status
        self.detalle = detalle


class APIClient:
    """Wrapper fino sobre `requests.Session` con helpers CRUD para la API DRF."""

    def __init__(self, base: str | None = None, timeout: int = 15):
        self.base = (base or _base_url()).rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()

    # -- infraestructura ---------------------------------------------------
    def _url(self, path: str) -> str:
        return f"{self.base}/{path.lstrip('/')}"

    def _handle(self, resp: requests.Response) -> Any:
        if resp.status_code == 204:  # No Content (DELETE)
            return None
        if not resp.ok:
            try:
                detalle = resp.json()
            except ValueError:
                detalle = resp.text
            raise APIError(
                f"HTTP {resp.status_code} en {resp.url}", resp.status_code, detalle
            )
        if resp.content:
            return resp.json()
        return None

    # -- verbos CRUD -------------------------------------------------------
    def list(self, recurso: str, **params) -> list[dict]:
        """GET /recurso/ (limpia params None). Agrega TODAS las páginas si la API pagina.

        La API DRF pagina (PAGE_SIZE=50): quedarse con la primera página truncaba las
        vistas a 50 filas y ocultaba datos (p. ej. una semana recién copiada a una fecha
        que cae fuera de las primeras 50 no aparecía). Seguimos los enlaces `next` hasta
        agotar los resultados.
        """
        limpios = {k: v for k, v in params.items() if v not in (None, "")}
        data = self._handle(
            self.session.get(self._url(f"{recurso}/"), params=limpios, timeout=self.timeout)
        )
        if not isinstance(data, dict) or "results" not in data:  # respuesta sin paginar
            return data or []
        items = list(data["results"])
        siguiente = data.get("next")
        while siguiente:  # `next` es una URL absoluta; es None cuando no hay más páginas
            data = self._handle(self.session.get(siguiente, timeout=self.timeout))
            items.extend(data["results"])
            siguiente = data.get("next")
        return items

    def get(self, recurso: str, pk: int) -> dict:
        return self._handle(
            self.session.get(self._url(f"{recurso}/{pk}/"), timeout=self.timeout)
        )

    def create(self, recurso: str, payload: dict) -> dict:
        return self._handle(
            self.session.post(self._url(f"{recurso}/"), json=payload, timeout=self.timeout)
        )

    def update(self, recurso: str, pk: int, payload: dict, parcial: bool = True) -> dict:
        metodo = self.session.patch if parcial else self.session.put
        return self._handle(
            metodo(self._url(f"{recurso}/{pk}/"), json=payload, timeout=self.timeout)
        )

    def delete(self, recurso: str, pk: int) -> None:
        self._handle(self.session.delete(self._url(f"{recurso}/{pk}/"), timeout=self.timeout))

    # -- acciones extra ----------------------------------------------------
    def action(self, recurso: str, accion: str, **params) -> Any:
        """GET de una acción a nivel de colección, p. ej. tareas/resumen/."""
        limpios = {k: v for k, v in params.items() if v not in (None, "")}
        return self._handle(
            self.session.get(
                self._url(f"{recurso}/{accion}/"), params=limpios, timeout=self.timeout
            )
        )

    def post_action(self, recurso: str, accion: str, payload: dict | None = None):
        """POST a una acción de colección, p. ej. clases/copiar_semana/."""
        return self._handle(
            self.session.post(
                self._url(f"{recurso}/{accion}/"), json=payload or {}, timeout=self.timeout
            )
        )

    def download(self, path: str, **params) -> tuple[bytes, str]:
        """Descarga binaria (exportaciones). Devuelve (contenido, content_type)."""
        limpios = {k: v for k, v in params.items() if v not in (None, "")}
        resp = self.session.get(self._url(path), params=limpios, timeout=self.timeout)
        if not resp.ok:
            raise APIError(f"HTTP {resp.status_code} al descargar {resp.url}", resp.status_code)
        return resp.content, resp.headers.get("Content-Type", "application/octet-stream")

    def upload(self, recurso: str, accion: str, archivo, campo: str = "archivo") -> Any:
        """POST multipart de un archivo a una acción (p. ej. turnos-equipo/importar/)."""
        files = {campo: (archivo.name, archivo.getvalue())}
        return self._handle(
            self.session.post(
                self._url(f"{recurso}/{accion}/"), files=files, timeout=self.timeout
            )
        )

    def tv_canales(self, buscar: str | None = None) -> dict:
        """Endpoint especial de TV (fuera del router, ruta absoluta bajo /api)."""
        params = {"buscar": buscar} if buscar else {}
        return self._handle(
            self.session.get(self._url("tv/canales/"), params=params, timeout=self.timeout)
        )

    def ping(self) -> bool:
        """True si la API responde (usa la raíz del router DRF)."""
        try:
            resp = self.session.get(self._url("/"), timeout=5)
            return resp.ok
        except requests.RequestException:
            return False


@st.cache_resource
def get_client() -> APIClient:
    """Cliente único reutilizado entre reruns de Streamlit."""
    return APIClient()
