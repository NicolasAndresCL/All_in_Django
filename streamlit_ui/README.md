# UI Streamlit — All in Django

Interfaz visual (cliente) de la API REST de **All in Django**. No accede a la base de
datos ni al ORM: **habla con la API DRF por HTTP**, igual que cualquier consumidor externo.

```
streamlit_ui/
├── app.py            # entrada: st.set_page_config + st.navigation
├── api_client.py     # cliente HTTP centralizado (CRUD, acciones, export, upload, download)
│                     #   list() sigue la paginación de la API (todas las páginas, no solo 50)
├── gantt.py          # Gantt Plotly (personal + equipo)
├── run_ui.py         # lanzador: puerto 8501 o el siguiente libre (siempre arranca)
├── requirements.txt
├── run_app.bat
├── views/            # una vista por dominio
│   ├── inicio.py     # estado de conexión + conteos
│   ├── calendario.py # clases + turnos personales, copiar semana, PDF y Gantt
│   ├── liveops.py    # turnos equipo + importar/exportar + PDF con formato + Gantt equipo
│   ├── tareas.py     # dashboard (6 métricas + 6 gráficos) + CRUD + autocompletado
│   ├── notas.py      # crear/editar/exportar (md/txt) + preview
│   └── tv.py         # grilla de canales (solo lectura)
└── tests/            # api_client, run_ui, app, dashboard, Gantt y render de cada vista
```

## Uso

### Rápido: todo con el `.bat`

```powershell
streamlit_ui\run_app.bat
```

El `.bat`:
1. Localiza la raíz del proyecto y **reconoce/activa su `env\`** (falla claro si no existe).
2. Ejecuta `run_ui.py`, que **orquesta todo el arranque**.

### Con Python directamente

`run_ui.py` hace, en orden:

1. Si la API **no** responde ya, aplica migraciones y levanta `manage.py runserver`
   (como subproceso) y **espera a que conteste** antes de seguir.
2. Elige el puerto de la UI (8501 o el siguiente libre).
3. Lanza la **UI Streamlit** apuntando a esa API.

```powershell
python streamlit_ui\run_ui.py
```

Así la UI nunca arranca antes que la API y se evita el error *"No se pudo conectar
con la API"*. La API corre como **subproceso de la UI**: al cerrar la UI, la API se
detiene sola. Si ya tienes una API corriendo (p. ej. `python manage.py runserver` en
otra terminal), `run_ui.py` la **detecta y reutiliza** en vez de abrir otra.

### Puerto

La UI usa el puerto **8501** por defecto; si está ocupado, `run_ui.py` prueba el
siguiente libre (8502, 8503, …) para que **siempre arranque**. El puerto base se
puede cambiar con la variable de entorno `UI_PORT`:

```powershell
$env:UI_PORT = "8600"
python streamlit_ui\run_ui.py
```

## Configuración

La URL de la API se resuelve en este orden:

1. `st.secrets["API_BASE"]` (archivo `.streamlit/secrets.toml`)
2. Variable de entorno `API_BASE`
3. Por defecto: `http://localhost:8000/api`

Variables que entiende `run_ui.py`:

| Variable | Por defecto | Uso |
|---|---|---|
| `API_HOST` | `127.0.0.1` | host donde levanta/espera la API |
| `API_PORT` | `8000` | puerto de la API Django |
| `API_BASE` | `http://127.0.0.1:8000/api` | URL que consume la UI |
| `UI_PORT` | `8501` | puerto base de la UI (salta si está ocupado) |

```powershell
$env:API_PORT = "9000"
python streamlit_ui\run_ui.py     # API en :9000 y UI apuntando ahí
```

## Tests

Los tests no levantan el backend: mockean el HTTP con **`responses`**.

```powershell
pytest streamlit_ui\tests            # solo la UI
pytest                               # toda la suite (backend + UI)
```

`streamlit_ui/tests/conftest.py` añade `streamlit_ui/` al `sys.path` para poder
`import api_client` igual que hace Streamlit al ejecutar la app.

`test_views_render.py` ejecuta el `render()` de cada vista con
`streamlit.testing.v1.AppTest` (API mockeada) y verifica que dibuja sin excepción,
incl. los casos de API caída. Se importa la vista con
`AppTest.from_string("from views import X\nX.render()")` y se fija `API_BASE` antes de
importarla (lo cachea `@st.cache_resource` en `get_client()`).

## Dashboard de Registro de Tareas

La vista **Registro de Tareas** consume `/api/tareas/resumen/` y muestra:

- **6 métricas**: Tareas Totales, Proyectos Activos, Horas Acumuladas, **Racha Actual**
  (días consecutivos con actividad), Promedio Diario y Promedio Semanal.
- **6 gráficos Plotly**: jerarquía Proyecto/Tarea (sunburst), esfuerzo por proyecto,
  intensidad diaria (área), productividad semanal, actividad por día de la semana y
  progreso acumulado.

El cálculo (racha, promedios, series) se hace en el backend
(`apps/tareas/services.py`); la UI solo dibuja. Requiere `plotly` (en `requirements.txt`).

Además, el alta de tareas tiene **autocompletado**: proyecto y tarea se eligen de lo ya
registrado (selectbox), y al elegir un proyecto se filtran sus tareas; solo escribes texto
para lo nuevo (opción "➕ Nuevo…").

## Calendario y LiveOps: impresión, Gantt y semanas

- **Copiar / basar en otra semana**: en Calendario, crea el horario de una semana nueva a
  partir de otra ya registrada (`POST .../copiar_semana/`; reemplaza la semana destino).
- **Impresión PDF** (generada en el backend, `core/horarios_export.py`): horario de estudio,
  laboral, **maestro** (estudio + trabajo unificados) y turnos de equipo. Los botones
  descargan el PDF vía `api.download`.
- **Gantt semanal** (`gantt.py`, Plotly): vista personal (estudio + trabajo superpuestos) y
  de equipo (4 trabajadores). Se construye en la UI con los datos de la API.

## Autenticación (API_TOKEN)

La API exige token (`IsAuthenticated`): el cliente envía `Authorization: Token <clave>`.
El token se resuelve **`st.secrets` > variable de entorno `API_TOKEN`** y se crea con:

```powershell
python manage.py drf_create_token <usuario>     # o en el admin: Auth Token
```

Opciones para proveerlo:
- `streamlit_ui/.streamlit/secrets.toml` → `API_TOKEN = "..."` (recomendado en local;
  gitignored). `run_ui.py` lanza Streamlit con cwd en `streamlit_ui/` para que lo encuentre.
- Variable de entorno `API_TOKEN` (así lo recibe el contenedor de la UI en Compose).

Sin token, la vista de Inicio muestra el aviso "rechaza las credenciales (401)" con estas
instrucciones (la API se considera viva aunque devuelva 401: `ping()` vs `autenticado()`).

## Notas

- Los módulos **Reloj** y **Logins** del backend son management commands de escritorio
  (Selenium/tkinter), no endpoints HTTP: no se exponen en esta UI.
