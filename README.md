# 🧩 All in Django

Versión **Django + Django REST Framework** del proyecto `all_in_one` (que era 100% Streamlit).
Backend con API REST + Django Admin, configuración tipada con **pydantic-settings**,
metodología pythonic (clases, servicios, excepciones claras, logging, callbacks) y
tests con **pytest-django**.

## Stack

Python 3.14 · Django 6 · DRF · pydantic-settings · pandas/openpyxl · requests/beautifulsoup4 ·
fpdf2 · selenium · cachetools · dj-database-url · psycopg · gunicorn · whitenoise. Base de datos:
**SQLite** (`db.sqlite3`) por defecto, o **PostgreSQL** vía `DATABASE_URL` (ver
[Base de datos](#base-de-datos)). Despliegue declarativo: **Docker Compose · GitHub Actions ·
Terraform · Helm** (ver [Despliegue e IaC](#despliegue-e-iac)).

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
├── nicegui_ui/             # UI NiceGUI (cliente HTTP de la API) — ver su README
│   ├── main.py  layout.py  api_client.py  run_ui.py  run_app.bat
│   ├── views/               # una vista por dominio (tareas: dashboard con 6 gráficos Plotly)
│   ├── Dockerfile           # imagen de la UI
│   └── tests/               # cliente, charts, gantt y smoke de páginas (responses + nicegui.testing)
├── Dockerfile  docker/entrypoint.sh  docker-compose.yml  .dockerignore  .env.docker.example
├── .github/workflows/       # ci.yml (tests+build) · docker-publish.yml (GHCR)
├── infra/terraform/         # AWS EC2 + RDS (skeleton)
├── infra/helm/all-in-django/ # chart de Kubernetes
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

> ¿Prefieres no instalar nada localmente? Salta a [Despliegue e IaC](#despliegue-e-iac) y usa
> `docker compose up`.

## Despliegue e IaC

Toda la infraestructura está declarada como código. La orquestación imperativa
(`nicegui_ui/run_ui.py`) se reemplaza por artefactos declarativos por capa:

| Capa | Artefacto | Qué levanta |
|---|---|---|
| Imágenes | `Dockerfile` (API, gunicorn+WhiteNoise, no-root), `nicegui_ui/Dockerfile` (UI) | contenedores de API y UI |
| Orquestación local | `docker-compose.yml` | Postgres + API + UI (healthchecks + `depends_on`) |
| CI | `.github/workflows/ci.yml`, `docker-publish.yml` | tests+cobertura, build y push a GHCR |
| Nube | `infra/terraform/` (AWS EC2 + RDS) | infra en la nube (skeleton) |
| Kubernetes | `infra/helm/all-in-django/` | chart (API/UI/Postgres/Ingress) |

### Docker Compose (forma recomendada de levantar todo)

```bash
cp .env.docker.example .env.docker      # define SECRET_KEY (y credenciales de Postgres)
docker compose --env-file .env.docker up -d      # db (healthy) → api (migra) → ui

# Semilla de datos, una sola vez (monta fixtures/, excluido de la imagen):
docker compose --env-file .env.docker run --rm -v "${PWD}/fixtures:/app/fixtures" api \
    python manage.py loaddata fixtures/datos_sqlite.json
```

> Se pasa `--env-file .env.docker` para que Compose no lea el `.env` de Django (su `SECRET_KEY`
> con `$` provoca warnings de interpolación inofensivos).

- API/Admin: `http://localhost:8000/` · healthcheck `http://localhost:8000/healthz/`
- UI NiceGUI: `http://localhost:8501/`
- `docker compose down` conserva los datos (volumen `pgdata`).

La API se sirve con **gunicorn** y sirve sus estáticos (admin/DRF) con **WhiteNoise**. El
único acoplamiento UI↔API es el env `API_BASE` (en Compose, `http://api:8000/api`). El
`collectstatic` corre en el build de la imagen con un `SECRET_KEY` throwaway (el gate de
`core/conf.py` exige `SECRET_KEY` si `DEBUG=False`).

### Terraform (AWS) y Helm (Kubernetes)

Skeletons listos para `plan`/`lint`; ver [`infra/terraform/README.md`](infra/terraform/README.md)
y [`infra/helm/all-in-django/README.md`](infra/helm/all-in-django/README.md). Terraform
provisiona **RDS Postgres + EC2** (corre compose contra el RDS); el chart de Helm despliega
API/UI/Postgres con migraciones en un `initContainer` y probes a `/healthz/`. ⚠️ `terraform
apply` crea recursos de pago.

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

**Toda la API exige autenticación** (`IsAuthenticated`): token en el header
(`Authorization: Token <clave>`) o sesión (API navegable). Sin credenciales → `401`.
El token se obtiene en `/api/token/` (POST `{username, password}`), se crea con
`python manage.py drf_create_token <usuario>` o desde el admin (**Auth Token**).
Quedan públicos solo `/` (panel web) y `/healthz/` (readiness). Hay **rate limiting**:
60/min anónimos, 300/min autenticados y 10/min para `/api/token/` (configurables por env).

Las listas **paginan** (`PageNumberPagination`, `PAGE_SIZE=50`): la respuesta trae
`count`/`next`/`previous`/`results`. Un cliente que quiera todos los registros debe seguir
los enlaces `next` (así lo hace `nicegui_ui/api_client.py`).

| Endpoint | Métodos | Notas |
|---|---|---|
| `/api/token/` | POST `{username, password}` | devuelve el token de API (rate 10/min) |
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

## UI NiceGUI (opcional)

Cliente visual de la API en `nicegui_ui/` (no toca el ORM: consume la API por HTTP).
La forma más rápida de levantarlo todo (env + API + UI) es el `.bat`:

```powershell
nicegui_ui\run_app.bat
```

`run_ui.py` orquesta el arranque: si la API no responde ya, aplica migraciones, levanta
`manage.py runserver` (subproceso) y **espera a que conteste**; luego abre la UI (`python -m
nicegui_ui.main`) apuntando a esa API. Así se evita el error *"No se pudo conectar con la
API"*. Equivale a:

```powershell
python nicegui_ui\run_ui.py                # levanta API (si hace falta) + UI
```

La UI usa el puerto **8501** por defecto y, si está ocupado, salta al siguiente libre. Tema
**VS Code Dark High Contrast**; tablas compactas con scroll y gráficos Plotly con barra de
herramientas completa + **pantalla completa**. Incluye: **impresión PDF** (estudio, laboral,
maestro y equipo), **Gantt** semanal (personal y de equipo), **copiar/basar una semana en
otra**, **grilla semanal editable** de turnos y **autocompletado** de proyecto/tarea.
Detalles en [`nicegui_ui/README.md`](nicegui_ui/README.md).

Como la API exige token, la UI necesita **`API_TOKEN`** (variable de entorno o
`nicegui_ui/.env`); sin él, la vista de Inicio avisa "rechaza las credenciales (401)" con
las instrucciones. Créalo con `python manage.py drf_create_token <usuario>`.

## Management commands

```powershell
python manage.py importar_all_in_one [--data RUTA] [--force]   # migra datos de all_in_one
python manage.py normalizar_turnos 2026-06 [--cargar]          # Excel BASE → turnos legibles
python manage.py reloj                                          # reloj de escritorio (tkinter)
python manage.py login_menu                                     # logins Cisco/Sence (Selenium)
```

## Configuración / seguridad (pydantic-settings)

`core/conf.py` define un `Settings(BaseSettings)` tipado que lee `.env` y **valida**:
falla con un mensaje claro si `SECRET_KEY` no está definida —o es **débil** (< 50 chars
o < 5 distintos)— con `DEBUG=False`. Variables: `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`,
`CSRF_TRUSTED_ORIGINS`, `SECURE_HTTPS`, `THROTTLE_ANON/USER/TOKEN`, `DATABASE_URL`,
`CISCO_USER/PASS`, `SENCE_RUT`, `CLAVE_UNICA`, `ALL_IN_ONE_DATA`. El `.env` no se
versiona (`.gitignore`).

Endurecimiento aplicado:
- **Autenticación por token** en toda la API (`IsAuthenticated` + `TokenAuthentication`);
  solo `/` y `/healthz/` son públicos. Login por token en `/api/token/`.
- **Rate limiting** (DRF): 60/min anónimos · 300/min autenticados · 10/min en `/api/token/`
  (frena fuerza bruta). Configurable vía `THROTTLE_*`.
- **`SECURE_HTTPS=True`** (solo detrás de TLS real) activa: `SECURE_SSL_REDIRECT` (con
  `/healthz/` exento para los healthchecks), HSTS (1 año, subdominios, preload) y cookies
  `Secure` de sesión/CSRF. Con esto `manage.py check --deploy` queda **sin warnings**.
  En local/Compose se deja apagado porque se sirve HTTP plano.

## Tests

```powershell
pytest                                  # backend: lógica, modelos, API, servicios, scraper
pytest nicegui_ui/tests                 # UI: cliente + smoke de páginas (HTTP mockeado)
# Cobertura con coverage.py (vía pytest-cov):
pytest --cov=apps --cov=core --cov=nicegui_ui --cov-report=term-missing
```

164 tests en total: backend (Django + DRF, incl. dashboard/racha de tareas, PDFs de
impresión, copiar semanas, **upsert** de turnos y healthcheck `/healthz/`) + **seguridad**
(`test_seguridad.py`: 401 sin token, obtención/uso del token, rate limit del login con 429,
validación de `SECRET_KEY` débil y el toggle `SECURE_HTTPS`) + **tests unitarios con
`unittest.mock`** (`apps/liveops/test_mock.py`: `guardar_turnos` con el modelo mockeado y la
acción `importar` con los servicios mockeados, sin BD ni archivos) + cliente de la UI (api_client
—incl. que sigue **todas** las páginas de la API y envía el header `Authorization: Token`—) +
**smoke de las 6 páginas NiceGUI** con **`nicegui.testing.User`** (mock HTTP vía `responses`,
incl. casos 401/API caída) y las figuras Plotly (`charts.py`/`gantt.py`, funciones puras).
Los tests de API usan la fixture **`api`** (conftest raíz): `APIClient` autenticado que además
limpia el cache de throttling entre tests. Los de UI son `async` (`asyncio_mode=auto`).

**Cobertura ~83%** (coverage.py); los serializers de turnos, con el upsert, quedan al 100%.
Deps de test en `requirements-dev.txt` (`pytest`, `pytest-asyncio`, `pytest-django`,
`pytest-cov`, `coverage`, `responses`), que **incluye también `nicegui_ui/requirements.txt`**:
los tests de la UI importan `gantt.py`/`charts.py` y las vistas (usan plotly/nicegui) y sin
esas deps la recolección de pytest falla con exit 2. `unittest.mock` es de la stdlib.

## Autor

**Nicolás Andrés Cano Leal** — 2026 · LiveOps & BizOps · Python Backend · Data Automation
