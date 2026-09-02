"""
Tests de INTERACCION de la UI: tocar el widget y afirmar que algo cambio.

**Por que existen.** `test_paginas.py` abre cada ruta y comprueba que se dibuja, pero no
pulsa un solo boton: un formulario que renderiza perfecto y cuyo `on_click` esta roto —o
manda el payload equivocado— pasa esos once tests sin despeinarse. Aqui se ejercita el
flujo principal de cada pagina y se afirma el efecto: la peticion que sale hacia la API,
con su metodo, su ruta y su cuerpo.

Cada flujo se prueba en los DOS sentidos donde tiene sentido: que la accion valida llama a
la API, y que la invalida NO la llama (una validacion que solo se prueba con datos buenos
no esta probada).

No levantan el backend: `responses` intercepta el HTTP, igual que el resto de la suite.
"""

import asyncio
import json

import responses
from datos_api import BASE, TAREAS, mock_api
from nicegui import ui
from nicegui.testing import User

DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def _peticiones(rsps: responses.RequestsMock, metodo: str, sufijo: str) -> list[dict]:
    """Cuerpos JSON de las peticiones que salieron hacia `sufijo` con ese metodo."""
    return [
        json.loads(llamada.request.body or "{}")
        for llamada in rsps.calls
        if llamada.request.method == metodo and llamada.request.url.endswith(sufijo)
    ]


# ─── Calendario · alta de clase ──────────────────────────────────────────────
async def test_crear_clase_envia_el_payload_que_la_api_espera(user: User) -> None:
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        mock_api(rsps)
        rsps.post(f"{BASE}/clases/", json={"id": 2}, status=201)

        await user.open("/calendario")
        user.find("Asignatura").type("Álgebra")
        user.find("Crear clase").click()
        await user.should_see("Clase creada.")

        (enviado,) = _peticiones(rsps, "POST", "/clases/")
        assert enviado["asignatura"] == "Álgebra"
        assert enviado["dia"] == "Lunes"
        # La vista normaliza a lunes ISO y completa los segundos que espera el serializer.
        assert enviado["entrada"] == "08:00:00"
        assert enviado["semana_inicio"].endswith(("0", "1", "2", "3", "4", "5", "6", "7", "8", "9"))


async def test_crear_clase_sin_asignatura_no_llega_a_la_api(user: User) -> None:
    """El otro sentido: la validacion corta ANTES de la peticion, no despues de un 400."""
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        mock_api(rsps)
        rsps.post(f"{BASE}/clases/", json={"id": 2}, status=201)

        await user.open("/calendario")
        user.find("Crear clase").click()  # el campo Asignatura sigue vacio
        await user.should_see("Indica la asignatura.")

        assert _peticiones(rsps, "POST", "/clases/") == []


# ─── Calendario · copiar semana ──────────────────────────────────────────────
async def test_copiar_semana_manda_origen_y_destino(user: User) -> None:
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        mock_api(rsps)
        rsps.post(f"{BASE}/clases/copiar_semana/",
                  json={"copiadas": 3, "destino": "2026-07-06"})

        await user.open("/calendario")
        user.find("📋 Copiar / basar en otra semana").click()  # expansion cerrada por defecto
        user.find("📥 Copiar").click()
        await user.should_see("3 registros copiados")

        (enviado,) = _peticiones(rsps, "POST", "/clases/copiar_semana/")
        # El origen sale del select (la unica semana de los datos de ejemplo) y el destino
        # se normaliza al lunes de la semana escrita en el campo de fecha.
        assert enviado["origen"] == "2026-06-29"
        assert len(enviado["destino"]) == 10


# ─── Calendario · grilla semanal de turnos ───────────────────────────────────
async def test_guardar_semana_hace_upsert_de_los_siete_dias(user: User) -> None:
    """La grilla no da de alta dia a dia: guarda los 7 de una vez, y el serializer hace
    upsert por (semana, dia). Si se rompiera el bucle, faltarian dias sin ningun error."""
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        mock_api(rsps)
        rsps.post(f"{BASE}/turnos-personales/", json={"id": 1}, status=201)

        await user.open("/calendario")
        user.find("Turnos personales").click()  # pestaña
        user.find("Guardar semana").click()
        await user.should_see("guardada")

        enviados = _peticiones(rsps, "POST", "/turnos-personales/")
        assert [t["dia"] for t in enviados] == DIAS
        assert all(t["entrada"] == "18:00:00" and t["salida"] == "23:00:00" for t in enviados)


async def test_marcar_un_dia_libre_lo_envia_sin_horario(user: User) -> None:
    """Un turno libre va con es_libre=True y SIN entrada/salida: el modelo las calcula a
    None. Mandar horas en un dia libre es justo lo que el checkbox debe evitar."""
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        mock_api(rsps)
        rsps.post(f"{BASE}/turnos-personales/", json={"id": 1}, status=201)

        await user.open("/calendario")
        user.find("Turnos personales").click()
        user.find(marker="libre-Domingo").click()
        user.find("Guardar semana").click()
        await user.should_see("guardada")

        enviados = {t["dia"]: t for t in _peticiones(rsps, "POST", "/turnos-personales/")}
        assert enviados["Domingo"]["es_libre"] is True
        assert "entrada" not in enviados["Domingo"]
        assert enviados["Lunes"]["es_libre"] is False  # los demas no se contagian


# ─── Tareas · filtro por proyecto ────────────────────────────────────────────
async def test_filtrar_por_proyecto_deja_fuera_los_demas(user: User) -> None:
    """El filtro es client-side (`_filtrados`): recorta lo ya descargado sin volver a la
    API. Se afirma sobre las `rows` del ui.table y no con `should_see`, porque el
    contenido de una tabla Quasar vive en su propiedad `rows`, no como elementos hijos —
    un `should_see("tareaX")` pasaria en verde por el select del formulario de alta, que
    tambien lista los nombres de tarea. Un test que mira donde no es, no mira."""
    dos_proyectos = TAREAS + [{
        "id": 2, "fecha": "2026-07-02", "proyecto": "ProyectoB", "tarea": "tareaZ",
        "duracion": "01:00:00", "horas": 1.0,
    }]

    def tareas_en_pantalla() -> set[str]:
        (registros,) = user.find(kind=ui.table).elements
        return {fila["tarea"] for fila in registros.rows}

    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        mock_api(rsps, tareas=dos_proyectos)

        await user.open("/tareas")
        assert tareas_en_pantalla() == {"tareaX", "tareaZ"}

        # Se asigna el valor en vez de `click()` sobre la opcion: el popup de un
        # ui.select lo dibuja Quasar en el navegador y la simulacion de `User` no lo
        # despliega, asi que no hay ningun elemento "ProyectoB" que pulsar. Asignar
        # `.value` SI dispara el on_change (ValueElement._handle_value_change), que es la
        # logica bajo prueba: `cambia_filtro` -> `listado.refresh()`.
        # `with user.client` es obligatorio para mutar un elemento fuera de un handler:
        # es el mismo contexto en el que UserInteraction.clear() hace su trabajo.
        (filtro,) = user.find("Filtrar por proyecto").elements
        with user.client:
            filtro.value = "ProyectoB"
        await asyncio.sleep(0)  # el refresh del contenedor se despacha en el event loop

        assert tareas_en_pantalla() == {"tareaZ"}


# ─── Tema · el selector cambia la eleccion del usuario ───────────────────────
async def test_elegir_un_tema_lo_guarda_para_este_usuario(user: User) -> None:
    """El tema vive en `app.storage.user` (por navegador). Se guardo un tiempo en
    `app.storage.general` —ambito "todos los usuarios"— y se filtraba entre instancias."""
    from nicegui import app

    from nicegui_ui import tema as t

    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        mock_api(rsps)
        await user.open("/")
        assert t.tema_elegido() == t.TEMA_AUTO  # de fabrica, el personaje de cada pagina

        clave = next(iter(t.TEMAS))
        # El click va en la columna marcada, no en su etiqueta: quien escucha el evento es
        # el contenedor (ver layout._opcion), asi que pulsar el label no dispara nada.
        user.find(marker=f"tema-{clave}").click()

        assert app.storage.user["tema"] == clave
        assert t.tema_elegido() == clave  # y la funcion que lee la eleccion lo ve
