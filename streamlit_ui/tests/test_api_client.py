"""Tests del cliente HTTP de la UI (api_client), con respuestas de red mockeadas."""

import pytest
import responses

from api_client import APIClient, APIError

BASE = "http://testserver/api"


@pytest.fixture
def api():
    return APIClient(base=BASE)


# ─── autenticación ───────────────────────────────────────────────────────────
def test_token_pone_header_authorization():
    cliente = APIClient(base=BASE, token="abc123")
    assert cliente.session.headers["Authorization"] == "Token abc123"


def test_sin_token_no_hay_header(api):
    assert "Authorization" not in api.session.headers


def test_token_de_env(monkeypatch):
    monkeypatch.setenv("API_TOKEN", "desde-env")
    cliente = APIClient(base=BASE)
    assert cliente.session.headers["Authorization"] == "Token desde-env"


@responses.activate
def test_ping_true_con_401_y_autenticado_false():
    # La API viva pero sin token: ping() True (está arriba), autenticado() False.
    responses.get(f"{BASE}/", json={"detail": "no auth"}, status=401)
    cliente = APIClient(base=BASE)
    assert cliente.ping() is True
    assert cliente.autenticado() is False


# ─── list ────────────────────────────────────────────────────────────────────
@responses.activate
def test_list_desempaqueta_paginacion(api):
    responses.get(
        f"{BASE}/clases/",
        json={"count": 2, "results": [{"id": 1}, {"id": 2}]},
    )
    assert api.list("clases") == [{"id": 1}, {"id": 2}]


@responses.activate
def test_list_sigue_todas_las_paginas(api):
    # Regresión: la API pagina (PAGE_SIZE=50). Antes se devolvía solo la 1.ª página,
    # ocultando datos en la UI (p. ej. una semana recién copiada al final de la lista).
    # `list` debe seguir los enlaces `next` y agregar TODAS las páginas.
    responses.get(
        f"{BASE}/clases/",
        json={"count": 3, "next": f"{BASE}/clases/p2", "results": [{"id": 1}, {"id": 2}]},
    )
    responses.get(
        f"{BASE}/clases/p2",
        json={"count": 3, "next": None, "results": [{"id": 3}]},
    )
    assert api.list("clases") == [{"id": 1}, {"id": 2}, {"id": 3}]


@responses.activate
def test_list_lista_plana(api):
    responses.get(f"{BASE}/notas/", json=[{"id": 1}])
    assert api.list("notas") == [{"id": 1}]


@responses.activate
def test_list_omite_params_vacios(api):
    responses.get(f"{BASE}/tareas/", json=[])
    api.list("tareas", proyecto=None, semana_inicio="")
    # Ningún query param debe viajar (los vacíos se filtran).
    assert responses.calls[0].request.params == {}


@responses.activate
def test_list_pasa_params_validos(api):
    responses.get(f"{BASE}/turnos-equipo/", json=[])
    api.list("turnos-equipo", trabajador="Babi")
    assert responses.calls[0].request.params == {"trabajador": "Babi"}


# ─── CRUD ────────────────────────────────────────────────────────────────────
@responses.activate
def test_create(api):
    responses.post(f"{BASE}/notas/", json={"id": 5, "titulo": "N"}, status=201)
    assert api.create("notas", {"titulo": "N"}) == {"id": 5, "titulo": "N"}


@responses.activate
def test_get(api):
    responses.get(f"{BASE}/notas/5/", json={"id": 5})
    assert api.get("notas", 5) == {"id": 5}


@responses.activate
def test_update_usa_patch_por_defecto(api):
    responses.patch(f"{BASE}/notas/5/", json={"id": 5, "titulo": "X"})
    api.update("notas", 5, {"titulo": "X"})
    assert responses.calls[0].request.method == "PATCH"


@responses.activate
def test_update_put_cuando_no_parcial(api):
    responses.put(f"{BASE}/notas/5/", json={"id": 5})
    api.update("notas", 5, {"titulo": "X"}, parcial=False)
    assert responses.calls[0].request.method == "PUT"


@responses.activate
def test_delete_devuelve_none_en_204(api):
    responses.delete(f"{BASE}/notas/5/", status=204)
    assert api.delete("notas", 5) is None


# ─── acciones / descargas / uploads ──────────────────────────────────────────
@responses.activate
def test_action(api):
    responses.get(f"{BASE}/tareas/resumen/", json={"tareas": 3})
    assert api.action("tareas", "resumen") == {"tareas": 3}


@responses.activate
def test_download_devuelve_bytes_y_mime(api):
    responses.get(
        f"{BASE}/turnos-equipo/exportar/",
        body=b"PK\x03\x04",
        content_type="application/vnd.ms-excel",
    )
    contenido, mime = api.download("turnos-equipo/exportar/", formato="excel")
    assert contenido == b"PK\x03\x04" and mime == "application/vnd.ms-excel"


@responses.activate
def test_upload_envia_multipart(api):
    responses.post(f"{BASE}/turnos-equipo/importar/", json={"importadas": 1}, status=201)

    class _Archivo:
        name = "turnos.csv"

        def getvalue(self):
            return b"Fecha,Agente\n2026-06-01,Babi\n"

    assert api.upload("turnos-equipo", "importar", _Archivo()) == {"importadas": 1}
    assert "multipart/form-data" in responses.calls[0].request.headers["Content-Type"]


@responses.activate
def test_tv_canales_con_busqueda(api):
    responses.get(f"{BASE}/tv/canales/", json={"total": 1, "canales": [{"name": "Mega"}]})
    data = api.tv_canales("meg")
    assert data["total"] == 1
    assert responses.calls[0].request.params == {"buscar": "meg"}


# ─── errores ─────────────────────────────────────────────────────────────────
@responses.activate
def test_error_http_lanza_apierror_con_detalle(api):
    responses.post(f"{BASE}/clases/", json={"dia": ["obligatorio"]}, status=400)
    with pytest.raises(APIError) as exc:
        api.create("clases", {})
    assert exc.value.status == 400
    assert exc.value.detalle == {"dia": ["obligatorio"]}


@responses.activate
def test_ping_true_si_responde(api):
    responses.get(f"{BASE}/", json={})
    assert api.ping() is True


@responses.activate
def test_ping_false_si_falla_conexion(api):
    # Sin registrar la URL, responses lanza ConnectionError → ping lo captura.
    assert api.ping() is False
