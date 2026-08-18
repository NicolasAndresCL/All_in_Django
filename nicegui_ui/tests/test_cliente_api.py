"""Tests del cliente HTTP de la UI (api_client), con respuestas de red mockeadas."""

import pytest
import responses

from nicegui_ui.api_client import APIClient, APIError

BASE = "http://testserver/api"


@pytest.fixture
def api():
    return APIClient(base=BASE)


# ─── autenticación ───────────────────────────────────────────────────────────
def test_token_pone_header_authorization():
    cliente = APIClient(base=BASE, token="abc123")
    assert cliente.session.headers["Authorization"] == "Token abc123"


def test_sin_token_no_hay_header():
    # token="" explícito: el conftest define API_TOKEN en el entorno para los smoke
    # de páginas, así que aquí se anula para probar el caso "sin credenciales".
    cliente = APIClient(base=BASE, token="")
    assert "Authorization" not in cliente.session.headers


def test_token_de_env():
    # El autouse _entorno_api (conftest) define API_TOKEN=token-de-test en el entorno.
    # Sin monkeypatch: su teardown se intercalaba con el del autouse y re-filtraba
    # la variable al entorno global (rompía el test "sin token" de streamlit_ui).
    cliente = APIClient(base=BASE)
    assert cliente.session.headers["Authorization"] == "Token token-de-test"


@responses.activate
def test_ping_true_con_401_y_autenticado_false():
    # La API viva pero sin token: ping() True (está arriba), autenticado() False.
    responses.get(f"{BASE}/", json={"detail": "no auth"}, status=401)
    cliente = APIClient(base=BASE)
    assert cliente.ping() is True
    assert cliente.autenticado() is False


@responses.activate
def test_estado_auth_distingue_el_motivo_del_fallo():
    """El status es lo que permite a la UI no culpar al token de cualquier fallo: un
    429 del rate limit se anunciaba como "credenciales rechazadas"."""
    responses.get(f"{BASE}/", json={"detail": "throttled"}, status=429)
    cliente = APIClient(base=BASE)
    assert cliente.estado_auth() == (False, 429)


@responses.activate
def test_estado_auth_ok_devuelve_200():
    responses.get(f"{BASE}/", json={})
    assert APIClient(base=BASE).estado_auth() == (True, 200)


@responses.activate
def test_estado_auth_sin_respuesta_devuelve_status_none():
    """Sin URL registrada, `responses` lanza ConnectionError: la API no respondió, que
    no es lo mismo que rechazar las credenciales."""
    assert APIClient(base=BASE).estado_auth() == (False, None)


@responses.activate
def test_un_cliente_sin_token_lo_recupera_del_entorno(monkeypatch):
    """`get_client()` cachea el cliente todo el proceso: arrancar la UI antes de definir
    API_TOKEN dejaba un cliente sin cabecera para siempre. Ahora basta con recargar."""
    responses.get(f"{BASE}/", json={})
    cliente = APIClient(base=BASE, token="")
    assert cliente.tiene_token is False
    monkeypatch.setenv("API_TOKEN", "token-tardio")
    cliente.estado_auth()
    assert cliente.session.headers["Authorization"] == "Token token-tardio"


# ─── contar ──────────────────────────────────────────────────────────────────
@responses.activate
def test_contar_usa_el_count_de_la_paginacion_sin_recorrer_paginas(api):
    """Contar no debe descargar el recurso entero: 543 tareas en 11 peticiones para
    pintar un número era lo que agotaba el rate limit de la API."""
    responses.get(
        f"{BASE}/tareas/",
        json={"count": 543, "next": f"{BASE}/tareas/?page=2", "results": [{"id": 1}]},
    )
    assert api.contar("tareas") == 543
    assert len(responses.calls) == 1


@responses.activate
def test_contar_con_respuesta_sin_paginar(api):
    responses.get(f"{BASE}/notas/", json=[{"id": 1}, {"id": 2}])
    assert api.contar("notas") == 2


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
    # Firma explícita (nombre, bytes): en NiceGUI vienen del evento de ui.upload
    # (e.name, e.content.read()), sin objeto UploadedFile de por medio.
    responses.post(f"{BASE}/turnos-equipo/importar/", json={"importadas": 1}, status=201)
    contenido = b"Fecha,Agente\n2026-06-01,Babi\n"
    assert api.upload("turnos-equipo", "importar", "turnos.csv", contenido) == {"importadas": 1}
    assert "multipart/form-data" in responses.calls[0].request.headers["Content-Type"]
    assert b"turnos.csv" in responses.calls[0].request.body


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
