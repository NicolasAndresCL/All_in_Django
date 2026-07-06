"""
Tests unitarios de LiveOps con `unittest.mock`: aíslan la lógica de servicios y
del ViewSet sin tocar la base de datos ni leer archivos reales.

- `guardar_turnos`: se mockea el modelo `TurnoEquipo` para verificar callbacks
  (`on_ok`/`on_error`), el conteo y el error cuando no se guarda nada.
- Acción `importar` del ViewSet: se mockean los servicios (`leer_tabla`,
  `preparar_turnos_equipo`, `guardar_turnos`) para probar solo la orquestación.
"""

from unittest import mock

import pytest

from core.exceptions import ArchivoInvalidoError, ImportacionError

from . import services, views

FILA_LIBRE = {
    "semana_inicio": "2026-06-01", "trabajador": "Babi", "dia": "Lunes",
    "entrada": None, "salida": None, "es_libre": True,
}


# ─── guardar_turnos (modelo mockeado, sin BD) ────────────────────────────────
def test_guardar_turnos_llama_on_ok_con_conteo():
    """Con dos filas OK, guarda 2 y llama on_ok(2); nunca on_error."""
    on_ok, on_error = mock.Mock(), mock.Mock()
    filas = [FILA_LIBRE, {**FILA_LIBRE, "trabajador": "Nico"}]

    with mock.patch.object(services, "TurnoEquipo") as ModeloMock:
        ModeloMock.objects.filter.return_value.first.return_value = None  # siempre nuevo

        guardadas = services.guardar_turnos(filas, on_ok=on_ok, on_error=on_error)

    assert guardadas == 2
    on_ok.assert_called_once_with(2)
    on_error.assert_not_called()
    # Se llamó a save() una vez por fila (sobre la instancia nueva mockeada).
    assert ModeloMock.return_value.save.call_count == 2


def test_guardar_turnos_on_error_y_lanza_si_todo_falla():
    """Si save() revienta en todas las filas, avisa por on_error y lanza ImportacionError."""
    on_error = mock.Mock()

    with mock.patch.object(services, "TurnoEquipo") as ModeloMock:
        ModeloMock.objects.filter.return_value.first.return_value = None
        ModeloMock.return_value.save.side_effect = RuntimeError("db caída")

        with pytest.raises(ImportacionError):
            services.guardar_turnos([FILA_LIBRE], on_error=on_error)

    on_error.assert_called_once()
    # El mensaje del callback incluye trabajador y día de la fila fallida.
    (msg,) = on_error.call_args.args
    assert "Babi" in msg and "Lunes" in msg


def test_guardar_turnos_error_parcial_no_lanza():
    """Si al menos una fila se guarda, no lanza aunque otra falle."""
    on_ok, on_error = mock.Mock(), mock.Mock()
    filas = [FILA_LIBRE, {**FILA_LIBRE, "trabajador": "Nico"}]

    with mock.patch.object(services, "TurnoEquipo") as ModeloMock:
        ModeloMock.objects.filter.return_value.first.return_value = None
        # Primera fila OK, segunda falla.
        ModeloMock.return_value.save.side_effect = [None, ValueError("x")]

        guardadas = services.guardar_turnos(filas, on_ok=on_ok, on_error=on_error)

    assert guardadas == 1
    on_ok.assert_called_once_with(1)
    on_error.assert_called_once()


def test_guardar_turnos_lista_vacia_no_lanza():
    """Sin filas no hay nada que guardar y no se considera error."""
    with mock.patch.object(services, "TurnoEquipo"):
        assert services.guardar_turnos([]) == 0


# ─── acción importar del ViewSet (servicios mockeados, sin archivo real) ──────
def _request_con_archivo(nombre="turnos.csv"):
    request = mock.Mock()
    archivo = mock.Mock()
    archivo.name = nombre
    request.FILES.get.return_value = archivo
    return request, archivo


def test_importar_orquesta_los_servicios():
    """La acción encadena leer_tabla → preparar → guardar y arma la respuesta 201."""
    request, archivo = _request_con_archivo()

    with mock.patch.object(views, "leer_tabla", return_value="DATAFRAME") as m_leer, \
         mock.patch.object(views, "preparar_turnos_equipo",
                           return_value=(["f1", "f2"], {"agentes": ["Babi"], "semanas": []}, [])) as m_prep, \
         mock.patch.object(views, "guardar_turnos", return_value=2) as m_guardar:

        resp = views.TurnoEquipoViewSet().importar(request)

    assert resp.status_code == 201
    assert resp.data["importadas"] == 2
    assert resp.data["agentes"] == ["Babi"]
    m_leer.assert_called_once_with(archivo, "turnos.csv")
    m_prep.assert_called_once_with("DATAFRAME")
    m_guardar.assert_called_once()
    # guardar_turnos recibe las filas y callbacks on_ok/on_error.
    assert m_guardar.call_args.args[0] == ["f1", "f2"]
    assert "on_ok" in m_guardar.call_args.kwargs and "on_error" in m_guardar.call_args.kwargs


def test_importar_sin_archivo_lanza_archivo_invalido():
    """Sin campo 'archivo' la acción lanza ArchivoInvalidoError (→ 400 vía handler)."""
    request = mock.Mock()
    request.FILES.get.return_value = None

    with pytest.raises(ArchivoInvalidoError):
        views.TurnoEquipoViewSet().importar(request)


def test_importar_propaga_errores_de_preparacion():
    """Los errores de fila (preparar) viajan en la respuesta junto al conteo."""
    request, _ = _request_con_archivo()

    with mock.patch.object(views, "leer_tabla", return_value="DF"), \
         mock.patch.object(views, "preparar_turnos_equipo",
                           return_value=(["f1"], {"agentes": ["Nico"], "semanas": []},
                                         ["Fila 5: sin fecha."])), \
         mock.patch.object(views, "guardar_turnos", return_value=1):

        resp = views.TurnoEquipoViewSet().importar(request)

    assert resp.data["importadas"] == 1
    assert "Fila 5: sin fecha." in resp.data["errores"]
