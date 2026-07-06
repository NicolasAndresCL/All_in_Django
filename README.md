# 🧩 All in Django

Versión **Django + Django REST Framework** del proyecto `all_in_one` (que era Streamlit).
Backend con API REST + Django Admin, configuración tipada con **pydantic-settings**,
metodología pythonic (clases, servicios, excepciones claras, logging, callbacks) y
tests con **pytest-django**.

## Stack

Python 3.14 · Django 6 · DRF · pydantic-settings · pandas/openpyxl · requests/beautifulsoup4 ·
fpdf2 · selenium · cachetools · dj-database-url · psycopg. Base de datos: **SQLite**
(`db.sqlite3`) por defecto, o **PostgreSQL** vía `DATABASE_URL` (ver [Base de datos](#base-de-datos)).

## Estructura

```
all_in_django/
├── manage.py
├── config/                  # proyecto Django (settings, urls, wsgi/asgi)
│   ├── settings.py          # alimentado por core.conf (pydantic)
│   └── urls.py              # /admin/ + /api/ (router DRF) + /api/tv/canales/
├── core/                    # utilidades compartidas (sin modelos)
│   ├── conf.py              # Settings(BaseSettings) tipado y validado
│   ├── logging.py  exceptions.py
│   ├── horarios.py          # calcular_horas_turno, get_semana_inicio, hora_a_decimal
│   ├── export.py            # Excel (openpyxl) + PDF genérico (fpdf2)
│   ├── horarios_export.py   # PDFs con formato: estudio, laboral, equipo, maestro
│   └── api.py               # ExportMixin para los ViewSets
├── apps/
│   ├── calendario/          # Clase, TurnoPersonal
│   ├── liveops/             # TurnoEquipo (+ importar CSV/Excel + normalizar_turnos)
│   ├── tareas/              # Registro (+ resumen)
│   ├── notas/               # Nota (+ exportar md/txt)
│   ├── tv/                  # scraper de canales (solo lectura)
│   └── extras/              # commands: importar_all_in_one, reloj, login_menu
├── streamlit_ui/            # UI Streamlit (cliente HTTP de la API) — ver su README
│   ├── app.py  api_client.py  run_ui.py  run_app.bat
│   ├── views/               # una vista por dominio (tareas: dashboard con 6 gráficos Plotly)
│   └── tests/               # api_client, run_ui, dashboard y smoke de cada vista (responses + AppTest)
├── .env / .env.example  requirements.txt  requirements-dev.txt  pytest.ini  conftest.py
```

## Puesta en marcha

```powershell
cd c:\dev\projects\all_in_django
python -m venv env
env\Scripts\activate
pip install -r requirements-dev.txt

copy .env.example .env            # edita SECRET_KEY (o deja DEBUG=True para local)
python manage.py migrate
python manage.py importar_all_in_one   # migra datos desde all_in_one
python manage.py createsuperuser       # para /admin/
python manage.py runserver
```

- API navegable: `http://127.0.0.1:8000/api/`
- Admin: `http://127.0.0.1:8000/admin/`

## Base de datos

Sin `DATABASE_URL` la app usa **SQLite** (`db.sqlite3`), cero configuración. Para
**PostgreSQL**, `config/settings.py` arma la conexión desde `DATABASE_URL` con
`dj-database-url` (driver `psycopg` v3).

**Migrar de SQLite a PostgreSQL** (conservando los datos):

```powershell
# 1) Crear rol + base en Postgres (psql como superusuario 'postgres')
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -c "CREATE ROLE all_in_django LOGIN PASSWORD 'changeme';"
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -c "CREATE DATABASE all_in_django OWNER all_in_django;"

# 2) Volcar los datos actuales desde SQLite (ya generado en fixtures/datos_sqlite.json)
$env:PYTHONUTF8=1
python manage.py dumpdata --natural-foreign --natural-primary `
  -e contenttypes -e auth.permission -e admin.logentry -e sessions.session `
  --indent 2 -o fixtures/datos_sqlite.json

# 3) Apuntar a Postgres en .env y crear el esquema + cargar los datos
#    DATABASE_URL=postgres://all_in_django:changeme@localhost:5432/all_in_django
python manage.py migrate
python manage.py loaddata fixtures/datos_sqlite.json
```

El volcado usa **claves naturales** y excluye `contenttypes`/`auth.permission` (los recrea
`migrate`), por lo que carga limpio en la base nueva. Los campos calculados
(`horas`, `bruto/neto/extra`) viajan en el volcado, no se recalculan al cargar.

`fixtures/` está en `.gitignore`: contiene datos reales (horarios, tareas y notas
personales), no fixtures de test para versionar. Tras un `loaddata` con PKs explícitas,
Postgres no avanza las secuencias de autoincremento: resetéalas con
`django.db.connection.ops.sequence_reset_sql` (o crea un registro de prueba y bórralo)
antes de dar altas nuevas desde la API/UI, o chocarán con "duplicate key".

## API

Las listas **paginan** (`PageNumberPagination`, `PAGE_SIZE=50`): la respuesta trae
`count`/`next`/`previous`/`results`. Un cliente que quiera todos los registros debe seguir
los enlaces `next` (así lo hace `streamlit_ui/api_client.py`).

| Endpoint | Métodos | Notas |
|---|---|---|
| `/api/clases/` | GET/POST/PUT/DELETE | `?semana_inicio=` · `horas` calculado |
| `/api/clases/imprimir/?semana_inicio=` | GET | PDF con formato del horario de estudio |
| `/api/clases/imprimir_maestro/?semana_inicio=` | GET | PDF unificado (estudio + trabajo) |
| `/api/clases/copiar_semana/` | POST `{origen, destino}` | crea una semana basándose en otra |
| `/api/turnos-personales/` | CRUD | bruto/neto/extra calculados · POST hace **upsert** por (semana, día): reescribir un día lo reemplaza |
| `/api/turnos-personales/imprimir/?semana_inicio=` | GET | PDF con formato del horario laboral |
| `/api/turnos-personales/copiar_semana/` | POST `{origen, destino}` | copia turnos entre semanas |
| `/api/turnos-equipo/` | CRUD | `?semana_inicio=`, `?trabajador=` · POST hace **upsert** por (semana, trabajador, día) |
| `/api/turnos-equipo/importar/` | POST (multipart `archivo`) | importa CSV/Excel |
| `/api/turnos-equipo/imprimir/?semana_inicio=` | GET | PDF con formato de turnos del equipo |
| `/api/tareas/` | CRUD | `?proyecto=` |
| `/api/tareas/resumen/` | GET | dashboard: racha de días, promedios y series (por día/semana/proyecto/tarea) |
| `/api/notas/` | CRUD | |
| `/api/notas/{id}/exportar/?fmt=md\|txt` | GET | descarga la nota |
| `/api/tv/canales/?buscar=` | GET | canales (scraping, cache 1h) |
| `/api/<recurso>/exportar/?formato=excel\|pdf` | GET | export en clases/turnos/tareas |

## UI Streamlit (opcional)

Cliente visual de la API en `streamlit_ui/` (no toca el ORM: consume la API por HTTP).
La forma más rápida de levantarlo todo (env + API + UI) es el `.bat`:

```powershell
streamlit_ui\run_app.bat
```

`run_ui.py` orquesta el arranque: si la API no responde ya, aplica migraciones, levanta
`manage.py runserver` (subproceso) y **espera a que conteste**; luego abre la UI apuntando
a esa API. Así se evita el error *"No se pudo conectar con la API"*. Equivale a:

```powershell
python streamlit_ui\run_ui.py              # levanta API (si hace falta) + UI
```

La UI usa el puerto **8501** por defecto y, si está ocupado, salta al siguiente libre.
Al cerrar la UI, la API que levantó se detiene sola. Incluye: **impresión PDF** (estudio,
laboral, maestro y equipo), **Gantt** semanal (personal y de equipo), **copiar/basar una
semana en otra** y **autocompletado** de proyecto/tarea en Registro de Tareas. Detalles en
[`streamlit_ui/README.md`](streamlit_ui/README.md).

## Management commands

```powershell
python manage.py importar_all_in_one [--data RUTA] [--force]   # migra datos de all_in_one
python manage.py normalizar_turnos 2026-06 [--cargar]          # Excel BASE → turnos legibles
python manage.py reloj                                          # reloj de escritorio (tkinter)
python manage.py login_menu                                     # logins Cisco/Sence (Selenium)
```

## Configuración / seguridad (pydantic-settings)

`core/conf.py` define un `Settings(BaseSettings)` tipado que lee `.env` y **valida**:
falla con un mensaje claro si `SECRET_KEY` no está definida con `DEBUG=False`. Variables:
`SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `CISCO_USER/PASS`, `SENCE_RUT`, `CLAVE_UNICA`,
`ALL_IN_ONE_DATA`. El `.env` no se versiona (`.gitignore`).

## Tests

```powershell
pytest                                  # backend: lógica, modelos, API, servicios, scraper
pytest streamlit_ui/tests               # UI: api_client + render de cada vista (HTTP mockeado)
# Cobertura con coverage.py (vía pytest-cov):
pytest --cov=apps --cov=core --cov=streamlit_ui --cov-report=term-missing
```

109 tests en total: backend (Django + DRF, incl. dashboard/racha de tareas, PDFs de
impresión, copiar semanas y **upsert** de turnos) + **tests unitarios con `unittest.mock`**
(`apps/liveops/test_mock.py`: `guardar_turnos` con el modelo mockeado y la acción `importar`
con los servicios mockeados, sin BD ni archivos) + cliente de la UI (api_client —incl. que
sigue **todas** las páginas de la API—, arranque de API, dashboard y Gantt) + **smoke de las
6 vistas Streamlit** (cada `render()` con la API mockeada vía `responses` +
`streamlit.testing.v1.AppTest`, incl. casos de API caída).

**Cobertura ~83%** (coverage.py); los serializers de turnos, con el upsert, quedan al 100%.
Deps de test en `requirements-dev.txt` (`pytest`, `pytest-django`, `pytest-cov`, `coverage`,
`responses`); `unittest.mock` es de la stdlib.

## Autor

**Nicolás Andrés Cano Leal** — 2026 · LiveOps & BizOps · Python Backend · Data Automation
