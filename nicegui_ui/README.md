# UI NiceGUI — All in Django

Cliente visual de la API REST (Django + DRF) construido con **NiceGUI**. **No toca el ORM
ni la base de datos**: consume la API por HTTP (`api_client.py`), igual que cualquier
cliente externo. Sustituye a la antigua UI Streamlit.

## Estructura

```
nicegui_ui/
├── main.py            # @ui.page por vista (6 rutas) + ui.run (puerto 8501)
├── layout.py          # shell(): tema VS Code Dark High Contrast + header/drawer + helpers
│                       #   (metric_card, tabla con scroll, grafico con fullscreen)
├── api_client.py      # cliente HTTP (CRUD, acciones, export, upload, download, paginación)
├── charts.py          # construir_figuras: las 6 figuras Plotly del dashboard (función pura)
├── gantt.py           # Gantt Plotly (personal + equipo)
├── views/             # una vista por dominio: inicio, calendario, liveops, tareas, notas, tv
├── tests/             # nicegui.testing User + responses (páginas), cliente, charts, gantt
├── Dockerfile  run_ui.py  run_app.bat  requirements.txt
```

## Arranque

Local (levanta API + UI, como el `.bat`):

```powershell
nicegui_ui\run_app.bat
# o:  python nicegui_ui\run_ui.py     (migrate + runserver si hace falta, luego la UI)
```

`run_ui.py` orquesta: si la API no responde, aplica migraciones, levanta `manage.py
runserver` y espera a que conteste; luego abre la UI en el puerto **8501** (o el siguiente
libre). La UI corre con `python -m nicegui_ui.main`.

Standalone (con el backend ya arriba):

```powershell
python -m nicegui_ui.main        # UI_PORT=8501 por defecto
```

## Autenticación (API_TOKEN)

La API exige token (`IsAuthenticated`): el cliente envía `Authorization: Token <clave>`.
El token se lee de la variable de entorno **`API_TOKEN`** (o de `nicegui_ui/.env`, cargado
con python-dotenv; gitignored). Se crea con:

```powershell
python manage.py drf_create_token <usuario>     # o en el admin: Auth Token
```

Sin token, la vista de Inicio muestra el aviso "rechaza las credenciales (401)" con estas
instrucciones (la API se considera viva aunque devuelva 401: `ping()` vs `autenticado()`).
La URL de la API se configura con `API_BASE` (default `http://localhost:8000/api`).

## Detalles de UI

- **Tema**: VS Code *Dark High Contrast* (fondo negro, bordes cian de contraste, foco
  naranja), vía `ui.colors` + CSS global en `layout.py`.
- **Tablas** (`layout.tabla`): compactas, cabecera fija y scroll interno (estilo
  `st.dataframe`), no vuelcan todas las filas a lo largo de la página.
- **Gráficos** (`layout.grafico`): barra de herramientas Plotly completa + botón de
  **pantalla completa** (Fullscreen API + resize).
- **Turnos personales** (`views/calendario.py`): grilla semanal editable de 7 días; "cargar
  desde otra semana" precarga los valores en el formulario (asignando `.value`, sin la
  gimnasia de `session_state` que exigía Streamlit); "Guardar semana" hace upsert por día.
- Sin `st.rerun`: las secciones de datos son `@ui.refreshable` y se refrescan tras cada
  mutación.

## Tests

```powershell
pytest nicegui_ui/tests        # solo la UI
pytest                         # toda la suite (backend + UI)
```

Los tests de página usan **`nicegui.testing.User`** (fixture `user`, plugin activado en el
conftest raíz) que ejecuta `main.py` en un contexto simulado; el HTTP se mockea con
**`responses`** (mismos fixtures de datos que probaban la UI Streamlit). `charts.py` y
`gantt.py` se prueban como funciones puras. Requiere `pytest-asyncio` (`asyncio_mode=auto`
en `pytest.ini`).

## Notas

- Los módulos **Reloj** y **Logins** del backend son management commands de escritorio
  (Selenium/tkinter), no endpoints HTTP: no se exponen en esta UI.
- Los módulos se importan **cualificados** (`nicegui_ui.*`); por eso el contenedor arranca
  con `python -m nicegui_ui.main`.
