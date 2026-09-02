"""
test_contrato_api.py — La coleccion Postman no puede quedarse atras de la API.

Una coleccion de pruebas HTTP envejece en silencio: se anade un endpoint, nadie escribe su
peticion, y la coleccion sigue en verde probando lo de siempre. Estos tests cierran esa
puerta comparando el **esquema OpenAPI** (que drf-spectacular genera del propio codigo,
asi que no puede desactualizarse) con lo que la coleccion realmente visita.

No hacen red ni levantan nada: leen el JSON de `postman/` y generan el esquema en memoria.
Las pruebas de verdad, contra una API viva, las corre `scripts\\probar_api.ps1`.
"""

import json
import re
from pathlib import Path

import pytest
from drf_spectacular.generators import SchemaGenerator

RAIZ = Path(__file__).resolve().parent
COLECCION = RAIZ / "postman" / "all_in_django.postman_collection.json"
ENTORNO = RAIZ / "postman" / "local.postman_environment.json"

# Rutas del esquema que la coleccion NO prueba, y por que. La lista es corta a proposito:
# es mas facil justificar una excepcion que descubrir un hueco meses despues.
SIN_COBERTURA = {
    # Ya se ejercita entera al importar el CSV; un 422 exige un archivo legible cuyas filas
    # fallen TODAS al guardar, que es un caso de laboratorio y no de contrato.
}


def _cargar_coleccion() -> dict:
    return json.loads(COLECCION.read_text(encoding="utf-8"))


def _peticiones(nodo) -> list:
    """Aplana el arbol de carpetas de una coleccion Postman a una lista de peticiones."""
    salida = []
    for item in nodo.get("item", []):
        if "request" in item:
            salida.append(item)
        else:
            salida.extend(_peticiones(item))
    return salida


def _normalizar(url: str) -> str:
    """URL de Postman -> ruta comparable con el esquema OpenAPI.

    '{{base_url}}/api/notas/{{nota_id}}/exportar/'  ->  '/api/notas/{id}/exportar/'
    '{{base_url}}/api/clases/99999999/'             ->  '/api/clases/{id}/'
    """
    ruta = url.split("?", 1)[0].replace("{{base_url}}", "")
    ruta = re.sub(r"\{\{[^}]+\}\}", "{id}", ruta)   # variables de Postman
    ruta = re.sub(r"/\d+/", "/{id}/", ruta)          # ids escritos a pelo
    return ruta if ruta.startswith("/") else "/" + ruta


@pytest.fixture(scope="module")
def esquema() -> dict:
    """Esquema OpenAPI generado en memoria (la misma fuente que sirve /api/schema/)."""
    return SchemaGenerator().get_schema(request=None, public=True)


@pytest.fixture(scope="module")
def cubiertas() -> set:
    """(metodo, ruta) que la coleccion visita de verdad."""
    return {
        (p["request"]["method"].lower(), _normalizar(p["request"]["url"]["raw"]))
        for p in _peticiones(_cargar_coleccion())
    }


def test_la_coleccion_es_json_valido_v21():
    c = _cargar_coleccion()
    assert c["info"]["schema"].endswith("v2.1.0/collection.json")
    assert _peticiones(c), "la coleccion no tiene ni una peticion"


def test_cada_peticion_afirma_algo():
    """Una peticion sin aserciones no prueba nada: solo hace ruido y tarda."""
    sin_tests = [
        p["name"]
        for p in _peticiones(_cargar_coleccion())
        if not any(e.get("listen") == "test" for e in p.get("event", []))
    ]
    assert not sin_tests, f"peticiones sin bloque de tests: {sin_tests}"


def test_la_coleccion_no_lleva_secretos():
    """El token y la clave se rellenan en ejecucion; el repositorio no los guarda."""
    for clave in ("token", "password"):
        for var in _cargar_coleccion().get("variable", []):
            if var["key"] == clave:
                assert not var["value"], f"la coleccion versiona un valor para '{clave}'"
    for var in json.loads(ENTORNO.read_text(encoding="utf-8"))["values"]:
        if var["key"] in ("password", "token"):
            assert not var["value"], f"el entorno versiona un valor para '{var['key']}'"


def test_todo_endpoint_del_esquema_esta_probado(esquema, cubiertas):
    """El test que sostiene todo lo demas.

    Si anades un endpoint (o un metodo) a la API y no lo anades a la coleccion, esto se
    pone rojo. Es la unica forma de que la coleccion no envejezca sola.
    """
    faltan = [
        f"{metodo.upper()} {ruta}"
        for ruta, operaciones in esquema["paths"].items()
        for metodo in operaciones
        if ruta not in SIN_COBERTURA and (metodo, ruta) not in cubiertas
    ]
    assert not faltan, (
        "Endpoints del esquema que la coleccion Postman no visita:\n  "
        + "\n  ".join(sorted(faltan))
        + "\n\nAnade la peticion en postman/all_in_django.postman_collection.json "
          "(o justifica la excepcion en SIN_COBERTURA)."
    )


def test_la_coleccion_no_apunta_a_endpoints_inexistentes(esquema, cubiertas):
    """El reves del anterior: peticiones que sobreviven a un endpoint ya borrado.

    Se toleran las rutas que el esquema no describe por naturaleza: `/healthz/`, `/` y
    `/metrics` son vistas Django planas (no DRF), `/api/` es la raiz del router y
    `/api/schema/` no se autodocumenta (`SERVE_INCLUDE_SCHEMA: False`).
    """
    conocidas = set(esquema["paths"]) | {"/healthz/", "/", "/api/", "/api/schema/", "/metrics"}
    huerfanas = sorted({ruta for _, ruta in cubiertas if ruta not in conocidas})
    assert not huerfanas, f"la coleccion llama a rutas que ya no existen: {huerfanas}"
