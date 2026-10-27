# UI NiceGUI — All in Django

Cliente visual de la API REST (Django + DRF) construido con **NiceGUI**. **No toca el ORM
ni la base de datos**: consume la API por HTTP (`api_client.py`), igual que cualquier
cliente externo. Sustituye a la antigua UI Streamlit.

## Estructura

```
nicegui_ui/
├── main.py            # @ui.page por vista (7 rutas) + ui.run (puerto 8501)
├── tema.py            # sistema visual: TEMAS (aurora + 16 personajes), defaults globales,
│                       #   ui.query('body') y el CSS/JS global (add_head_html shared=True)
├── plotly_tema.py     # plantilla Plotly `aid` + config() de plotly.js (puro, sin UI)
├── layout.py          # shell(): header/drawer responsivos, selector de tema, rejillas
│                       #   responsivas y helpers (metric_card, tabla, grafico, sin_datos)
├── api_client.py      # cliente HTTP (CRUD, acciones, export, upload, download, paginación)
├── charts.py          # construir_figuras: treemap, esfuerzo, calendario de actividad,
│                       #   semanal, día de la semana y acumulado (funciones puras)
│                       #   + figura_tendencia: barras semanales + recta de tareas/analitica/
├── gantt.py           # Gantt Plotly (personal + equipo) con eje de hora real
├── apagado.py         # apagado/reinicio programado del PC local (envuelve shutdown.exe)
├── static/fondos/     # personajes con alfa reconstruido (+ mini/ para la banda)
├── views/             # una vista por dominio: inicio, calendario, liveops, tareas,
│                       #   notas, tv, apagado. Tareas incluye la sección Analítica
│                       #   (tendencia + días atípicos, calculados en la API con
│                       #   scikit-learn) y el botón "Informe PDF" (seaborn, en la API)
├── tests/             # User + responses (páginas, interacción), cliente, charts, gantt,
│                       #   tema y test_visual.py (Playwright: CSS y responsividad medidos)
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

Sin token, la vista de Inicio explica qué hacer. El diagnóstico lo da
`APIClient.estado_auth() -> (ok, status)`, y la vista traduce el status a una causa:
falta de token, token rechazado (401/403 — suele ser un token de otra base de datos),
**429 de rate limit** (300/min por usuario: *no* es un problema de credenciales) o API
caída (`status is None`). Con un único sí/no, cualquier fallo se anunciaba como
credenciales inválidas y mandaba a buscar donde no era.

La portada cuenta registros con `APIClient.contar()`, que lee el `count` de la paginación:
**una** petición por recurso. Con `len(api.list(...))` se descargaban las 543 tareas en 11
peticiones para pintar el número 543, y una docena de recargas agotaban el rate limit.
La URL de la API se configura con `API_BASE` (default `http://localhost:8000/api`).

## Detalles de UI

- **Tema por defecto: Aurora austral** (2.2.0). Cielo nocturno azul noche con cortinas de
  aurora verde → violeta → rosa que se mueven despacio y estrellas que titilan (todo CSS
  procedural), superficies de vidrio, header con un filo de aurora y cifras en degradado.
  Contraste AA medido en cada color de texto; los botones primarios llevan tinta oscura.
- **16 temas por personaje** (estilo cubierta) en el selector de la esquina superior
  derecha; en **Auto**, cada página trae el suyo. La elección se guarda en
  `app.storage.user` (por navegador). El personaje va como marca de agua con un aura de
  `drop-shadow` sobre su silueta; la opacidad se calibra por figura
  (`scripts/preparar_fondos.py`).
- **El acento tiñe toda la interfaz**: header, drawer, tarjetas (degradado + borde + realce
  y encendido al hover), tablas, separadores, gráficos y menú del selector. Las cifras de
  las métricas van en `aid-cifra` (el acento; en aurora, un degradado).
- **Cubierta de barco** (`tema.CUBIERTA`): madera tenue procedural (gradientes CSS, 0 KB de
  assets) con tablones, juntas y vetas, fija al viewport y teñida con el acento. Va en el
  estilo **inline** de `body`: la utilidad `bg-black` de Quasar es
  `background: #000 !important` y ese shorthand borraba la imagen (el negro lo pinta la
  propia cubierta con `background-color`).
- **Movimiento**: todas las imágenes rebotan (`aid-rebote` desde el default global de
  `ui.image`, con la fase escalonada por posición) y la marca de agua se mece como el
  barco. El hover apaga la animación —el `transform` de una animación gana a cualquier
  regla, así que pausarla no bastaría— y `prefers-reduced-motion: reduce` lo deja todo
  quieto.
- **Personalización global antes que estilos elemento por elemento** (guía oficial
  `nicegui/llms.md`): `default_props`/`default_classes` por tipo de elemento en
  `tema.aplicar_defaults()`, `ui.query('body')` para la página, clases Tailwind en las
  vistas (incluida la responsividad) y `add_head_html(..., shared=True)` **solo** para lo
  inexpresable en Python: pseudo-elementos del fondo, `@keyframes`, `:fullscreen`,
  `@media (hover: none)` y el estilo interno de Plotly.
- **Responsiva** (celular, tablet, escritorio): drawer cerrado por debajo de 1024 px,
  gráficos a 1/2/3 columnas, métricas repartidas según cuántas son, formularios apilados en
  móvil y sin scroll horizontal de página a ningún ancho (medido con Playwright a 360, 412,
  768, 1280 y 1920 px).
- **Tablas** (`layout.tabla`): compactas, cabecera fija y scroll interno (estilo
  `st.dataframe`; en móvil, scroll horizontal dentro de la tabla).
- **Gráficos** (`layout.grafico(fig, titulo, alto, nombre)`): tarjeta con cabecera (título +
  **pantalla completa**, con respaldo para iPhone), altura que depende del ancho, plantilla
  Plotly propia (`plotly_tema.py`) en TODOS los gráficos, barra de herramientas reducida y
  oculta en táctil. Las figuras viven en `charts.py`/`gantt.py` como funciones puras.
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
