# 🧩 All in Django

[![CI](https://github.com/NicolasAndresCL/All_in_Django/actions/workflows/ci.yml/badge.svg)](https://github.com/NicolasAndresCL/All_in_Django/actions/workflows/ci.yml)

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
| Imágenes | `Dockerfile` (API, gunicorn+WhiteNoise, no-root, `HEALTHCHECK`), `nicegui_ui/Dockerfile` (UI) | contenedores de API y UI |
| Orquestación local | `docker-compose.yml` (build local) | Postgres 18 + API + UI (healthchecks + `depends_on`) |
| Respaldos | `scripts/respaldar_bd.ps1`, `scripts/restaurar_bd.ps1` | dumps `-Fc` verificados del volumen |
| CI | `.github/workflows/ci.yml` | lint → tests/cobertura + Postgres real + hardening → build **y arranque** |
| Publicación | `.github/workflows/docker-publish.yml` | push a GHCR en tags `v*` (semver+sha, **no** `latest`) |
| **CD** | `Jenkinsfile` + `docker-compose.deploy.yml` | deploy de GHCR por compose, con respaldo previo y **rollback** |
| Nube | `infra/terraform/` (AWS EC2 + RDS Postgres 18) | infra en la nube (skeleton) |
| Kubernetes | `infra/helm/all-in-django/` | chart (API/UI/Postgres 18/Ingress) |

### Docker Compose (forma recomendada de levantar todo)

```bash
cp .env.docker.example .env.docker   # SECRET_KEY, POSTGRES_* y API_TOKEN son OBLIGATORIOS
docker compose --env-file .env.docker up -d      # db (healthy) → api (migra) → ui
```

> Se pasa `--env-file .env.docker` para que Compose no lea el `.env` de Django (su `SECRET_KEY`
> con `$` provoca warnings de interpolación inofensivos).

- API/Admin: `http://localhost:8000/` · healthcheck `http://localhost:8000/healthz/`
- UI NiceGUI: `http://localhost:8501/`
- Postgres: `localhost:5433` (el 5432 se deja libre para un Postgres nativo, si lo hay)

**Los contenedores** se llaman `all_in_django` (API), `all_in_django-db` y `all_in_django-ui`;
el proyecto Compose es `all_in_django`, fijado con `name:` **dentro** del archivo — no depende
del directorio ni de `-p`, así que el compose de desarrollo y el de despliegue actúan sobre el
mismo stack en vez de crear dos paralelos. Como contrapartida, con `container_name` no se puede
escalar con `--scale` (irrelevante en un stack de un nodo).

Si otro stack de la máquina ya ocupa esos puertos, se cambian sin tocar el YAML:
`API_PORT` / `UI_PORT` / `DB_PORT` en `.env.docker`.

**Variables obligatorias**: el compose usa `${SECRET_KEY:?…}`, `${POSTGRES_PASSWORD:?…}` y
`${API_TOKEN:?…}`. Si falta alguna, el stack **no arranca** en vez de levantar "sano" con una
clave débil o con la UI devolviendo 401 en cada vista.

**Salud**: el `HEALTHCHECK` vive en las **imágenes**, no en el compose. Así lo hereda cualquier
`docker run` del artefacto de GHCR y existe una sola definición de "sano" (antes estaba
duplicada en los dos compose y podía divergir). La API comprueba `/healthz/` (un `SELECT 1`
real contra la base), la UI que su servidor responde.

#### El volumen y la trampa de Postgres 18

Los datos viven en el volumen **`all_in_django_pgdata`**. `docker compose down` (sin `-v`) los
conserva; solo `down -v` los borra.

⚠️ **`postgres:18` cambió el layout de datos** respecto a la 16:

| | `postgres:16-alpine` | `postgres:18-alpine` |
|---|---|---|
| `PGDATA` | `/var/lib/postgresql/data` | `/var/lib/postgresql/18/docker` |
| `VOLUME` | `/var/lib/postgresql/data` | `/var/lib/postgresql` |

Por eso el compose monta `pgdata:/var/lib/postgresql` y **no fija `PGDATA`**. Montar en la ruta
antigua con la imagen 18 haría que los datos se escribieran en un volumen **anónimo** y se
perdieran al recrear el contenedor, **sin un solo error en el log**. Misma corrección aplicada
al StatefulSet del chart de Helm.

Comprobar que el montaje es el correcto:

```bash
docker exec all_in_django-db sh -c 'echo $PGDATA; ls $PGDATA/PG_VERSION'
docker inspect all_in_django-db --format '{{range .Mounts}}{{.Name}} -> {{.Destination}}{{end}}'
# all_in_django_pgdata -> /var/lib/postgresql   (y PGDATA cae dentro)
```

### Respaldo y restauración

La base del contenedor es la fuente de verdad, así que tiene respaldo propio:

```powershell
.\scripts\respaldar_bd.ps1               # dump fechado a fixtures\, rota los 10 ultimos
.\scripts\respaldar_bd.ps1 -Conservar 30
.\scripts\restaurar_bd.ps1               # restaura el mas reciente (pide confirmacion)
.\scripts\restaurar_bd.ps1 -Archivo fixtures\all_in_django_20260830.dump -Force
```

Detalles que importan:

- Formato **custom (`-Fc`)**, no SQL plano: trae los `SEQUENCE SET`, así que tras restaurar
  **no hay que resetear secuencias** (a diferencia del camino `dumpdata`/`loaddata`).
- El dump se genera y se **verifica** (`pg_restore --list`) *dentro* del contenedor y solo
  después se saca con `docker cp`. Nunca por la tubería de PowerShell, que convierte la salida
  a texto y corrompería un binario.
- `restaurar_bd.ps1` saca un respaldo de seguridad **antes** de pisar nada, y muestra el censo
  de filas antes y después.
- `fixtures/` está en `.gitignore`: los dumps llevan datos personales reales.

### CD con Jenkins

El **CI se queda en GitHub Actions** (lint + tests + hardening + build/arranque, y publish a
GHCR en tags `v*`). El **CD lo hace Jenkins** (corriendo en Docker): un pipeline **declarativo**
(`Jenkinsfile`) que **despliega las imágenes ya publicadas** en el mismo daemon Docker donde vive
Jenkins, con `docker-compose.deploy.yml` (usa `image:` de GHCR, no `build:`).

**Flujo**: `git tag vX.Y.Z && git push --tags` → Actions publica `all-in-django-{api,ui}` a GHCR →
Job de Jenkins (parámetro **`IMAGE_TAG`**) → valida el tag → **respalda la base** → `pull` +
`up -d` → espera a que **API y UI** queden `healthy`. Las migraciones se aplican solas
(entrypoint de la API).

Lo que el pipeline hace por ti, y antes no:

| Etapa | Por qué está |
|---|---|
| **Validar `IMAGE_TAG`** | Aborta si es vacío o `latest`: esa etiqueta **no existe** en GHCR. Descubrirlo aquí cuesta segundos; descubrirlo en el `pull` deja el stack a medias. |
| **Respaldo previo** | `pg_dump -Fc` verificado con `pg_restore --list` **antes** de tocar nada, archivado como artefacto de la build. Un CD que reemplaza la API debe poder devolver los datos. |
| **Healthcheck de API *y* UI** | Antes solo se miraba la API: una UI sin token pasaba por despliegue correcto. |
| **Rollback automático** | Si algo falla, vuelve solo al último tag que quedó sano (`.jenkins-ultimo-tag-ok`). Antes solo imprimía logs y pedía relanzar a mano, justo cuando el servicio está caído. |

```bash
# Equivalente manual (lo que ejecuta el Jenkinsfile):
IMAGE_TAG=1.0.0 docker compose --env-file .env.docker -f docker-compose.deploy.yml pull
IMAGE_TAG=1.0.0 docker compose --env-file .env.docker -f docker-compose.deploy.yml up -d
```

> Ya no se pasa `-p`: el nombre de proyecto (`all_in_django`) está fijado con `name:` dentro de
> ambos compose. Antes, desarrollo usaba `all_in_django` (por el directorio) y este pipeline
> `-p all-in-django`: **dos stacks distintos para la misma app**, y el healthcheck buscaba un
> contenedor `all-in-django-api-1` que no existía.

**Prerequisitos en Jenkins**:
- Contenedor de Jenkins con **docker CLI + docker compose** y **`/var/run/docker.sock` montado**
  (despliega en el mismo daemon).
- Credencial **Secret file `all-in-django-env`** = contenido de `.env.docker` (SECRET_KEY fuerte,
  `POSTGRES_*`, `API_TOKEN`). El pipeline la materializa al workspace y la borra al terminar,
  junto con los dumps.
- Si los paquetes GHCR son **privados**: credencial **Username/Password `ghcr-credentials`**
  (usuario GitHub + PAT con `read:packages`) y marcar el parámetro `GHCR_PRIVATE`.

> **Nota (`latest`)**: Actions publica `{{version}}`/`{{major}}.{{minor}}`/`sha` pero **no
> `latest`** — pasa el semver publicado en `IMAGE_TAG` (p. ej. `1.0.0` o `1.0`). Valida el
> `Jenkinsfile` en tu Jenkins con el *Declarative Linter* o *Replay*.

### Terraform (AWS) y Helm (Kubernetes)

Skeletons listos para `plan`/`lint`; ver [`infra/terraform/README.md`](infra/terraform/README.md)
y [`infra/helm/all-in-django/README.md`](infra/helm/all-in-django/README.md). Terraform
provisiona **RDS Postgres 18 + EC2** (corre compose contra el RDS); el chart de Helm despliega
API/UI/Postgres 18 con migraciones en un `initContainer` y probes a `/healthz/`. ⚠️ `terraform
apply` crea recursos de pago.

Detalles que conviene conocer antes de usarlos:

- **Helm**: `image.tag` viene **vacío** y se resuelve al `appVersion` del `Chart.yaml`. Antes el
  default era `latest`, un tag que el CI **nunca publica**, así que un `helm install` con los
  valores de fábrica moría en `ImagePullBackOff` sin pista de por qué.
- **Helm**: el StatefulSet de Postgres monta el PVC en `/var/lib/postgresql` y **no fija
  `PGDATA`** — mismo motivo que en Compose (ver la trampa de Postgres 18 más arriba).
- **Terraform**: el RDS lleva `skip_final_snapshot = false` con `final_snapshot_identifier`,
  `backup_retention_period` (7 días por defecto) y `deletion_protection`. Antes un `destroy`
  se llevaba la instancia **sin dejar copia**.

## Base de datos

`config/settings.py` arma la conexión desde `DATABASE_URL` con `dj-database-url` (driver
`psycopg` v3). Sin esa variable cae a **SQLite** (`db.sqlite3`), cero configuración.

**Dónde viven los datos, según cómo levantes el proyecto:**

| Modo | Base | Persistencia |
|---|---|---|
| `docker compose up` (recomendado) | Postgres 18 del contenedor `all_in_django-db` | volumen **`all_in_django_pgdata`** |
| `runserver` con `DATABASE_URL` | el Postgres que apunte esa URL | ese servidor |
| `runserver` sin `DATABASE_URL` | SQLite `db.sqlite3` | el archivo del repo |
| `pytest` | **siempre SQLite** salvo que exportes `DATABASE_URL` en el shell | base de test efímera |

Para que la app local use la base del contenedor, apunta el `.env` al puerto publicado:

```
DATABASE_URL=postgres://all_in_django:<clave>@localhost:5433/all_in_django
```

### Mover datos entre bases

**Entre dos Postgres del mismo mayor** (lo habitual: host ↔ contenedor) usa un dump lógico
`-Fc`, que es lo que hacen `scripts/respaldar_bd.ps1` y `scripts/restaurar_bd.ps1`. Trae los
`SEQUENCE SET`, así que las secuencias quedan al día solas.

```powershell
# Del Postgres nativo de Windows al contenedor, por ejemplo:
& "C:\Program Files\PostgreSQL\18\bin\pg_dump.exe" -U all_in_django -h localhost -p 5432 `
    -d all_in_django -Fc -f fixtures\origen.dump
.\scripts\restaurar_bd.ps1 -Archivo fixtures\origen.dump
```

⚠️ **Un directorio `PGDATA` NO es portable entre versiones mayores** (ni entre la 16 y la 18,
que además cambian de ruta). Para saltar de mayor, el único camino es el dump lógico.

**Entre motores distintos** (SQLite → Postgres, o al revés) el dump binario no sirve: hay que
pasar por `dumpdata`/`loaddata` de Django, que es agnóstico del motor.

```powershell
$env:PYTHONUTF8=1
python manage.py dumpdata --natural-foreign --natural-primary `
  -e contenttypes -e auth.permission -e admin.logentry -e sessions.session `
  --indent 2 -o fixtures/datos.json
# En la base destino: migrate, y despues
python manage.py loaddata fixtures/datos.json
```

El volcado usa **claves naturales** y excluye `contenttypes`/`auth.permission` (los recrea
`migrate`). Los campos calculados (`horas`, `bruto/neto/extra`) viajan en el volcado, no se
recalculan al cargar.

> Tras un `loaddata` con PKs explícitas, **Postgres no avanza las secuencias** de
> autoincremento: resetéalas con `django.db.connection.ops.sequence_reset_sql` antes de dar
> altas nuevas desde la API/UI, o chocarán con "duplicate key". Este problema **no existe** con
> los dumps `-Fc` de los scripts de respaldo, que sí traen los `setval`.

`fixtures/` está en `.gitignore`: contiene datos reales (horarios, tareas y notas personales),
no fixtures de test para versionar.

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
`nicegui_ui/.env`). Créalo con `python manage.py drf_create_token <usuario>`.

Si algo falla, la vista de Inicio **dice qué falla**, no siempre lo mismo: falta de token,
token rechazado (típico cuando es de otra base de datos: se creó en SQLite y la API ya
corre sobre Postgres), **429 por rate limit** —que no es un problema de credenciales— o la
API caída. Un token que aparece de pronto en el entorno se recoge al recargar la página,
sin reiniciar la UI.

### Identidad visual y temas

Sobre el tema base (VS Code Dark High Contrast) cada página tiene **un personaje de fondo
y un color de aura propios**. El reparto es semántico: Nami (la navegante) en Calendario,
Jinbe (el timonel) en LiveOps, Zoro en Tareas, Robin (la arqueóloga) en Notas, Brook en TV
y el sombrero colgado en Apagado. La portada abre con la tripulación al completo.

**Selector de tema** en la esquina superior derecha: los 16 personajes como temas
completos, más **Auto** (cada página con el suyo). La elección se guarda en
`app.storage.user`, es decir **por navegador**, y sobrevive a reiniciar la UI.

El personaje se dibuja como marca de agua a plena presencia —se le ve la cara— y el aura
sale de un `drop-shadow` calculado sobre su propia silueta, no de un rectángulo de color.
La **opacidad se calibra por personaje** midiendo su brillo medio: Brook, de frac negro,
necesita más del doble que un emblema claro para leerse igual de presente.

El color del personaje no se queda en el fondo: **tiñe toda la interfaz**. La barra
superior y el menú lateral arrancan del acento y se apagan a negro antes de la mitad; las
**tarjetas** llevan ese mismo degradado, borde y realce superior (y se encienden al pasar
el ratón); tablas, separadores, gráficos y el menú del selector siguen el mismo color. Las
cifras de las métricas van en `text-primary`, que es el acento activo.

Debajo de todo hay una **cubierta de barco**: una madera tenue de tablones, juntas y
vetas. Es **procedural** —gradientes CSS apilados, 0 KB de assets—, escala a cualquier
pantalla, no scrollea (`background-attachment: fixed`) y recoge algo del acento del
personaje. Va en el estilo **inline** de `body` (`tema.CUBIERTA`) por una razón concreta:
la utilidad `bg-black` de Quasar es `background: #000 !important` y ese shorthand borraba
la imagen de fondo, así que el negro lo pinta ahora la propia cubierta.

Y hay **movimiento**: todas las imágenes rebotan en bucle (`aid-rebote`, aplicado desde el
default global de `ui.image`, con la fase escalonada por posición para que la tripulación
no salte al unísono) y la marca de agua se **mece** despacio, como el barco. Al pasar el
ratón por encima manda el hover y la animación se detiene. Con
`prefers-reduced-motion: reduce`, todo queda quieto.

La legibilidad no se defiende apagando el arte, sino con **velos**: tarjetas, tablas,
campos y gráficos llevan fondo casi opaco con desenfoque. Medido sobre la UI real, el
contraste con texto blanco en las zonas donde hay texto es de **15:1** (WCAG AA pide 4,5:1).

#### Cómo se personaliza (guía oficial de NiceGUI)

Siguiendo `nicegui/llms.md` ("The Golden Rule – Python First"), la personalización va de
arriba abajo y el CSS crudo es el último recurso. Todo vive en
[`nicegui_ui/tema.py`](nicegui_ui/tema.py):

| Nivel | Qué hace | Dónde |
|---|---|---|
| `default_props` / `default_classes` | Aspecto por tipo de elemento (campos `outlined dense`, tablas, tarjetas), aplicado UNA vez al arrancar | `tema.aplicar_defaults()` |
| `ui.query('body')` | Estilado de la página: variables del tema **y la cubierta de madera** (la guía marca `add_head_html` para esto como antipatrón; aquí además es lo único que funciona) | `tema.aplicar_a_pagina()` |
| Clases **Tailwind** | Composición y espaciado en cada vista | vistas y `layout.py` |
| `ui.add_head_html(..., shared=True)` | SOLO lo inexpresable en Python: `body::before/::after` con `mask-image` y `drop-shadow`, y los `@keyframes` del rebote y del mecido | `tema.instalar()` |

Gracias a los defaults globales desaparecieron **21 repeticiones** de
`.props("outlined dense")` en las vistas, y el CSS se inyecta **una sola vez** en lugar
de en cada render de página.

#### Regenerar los assets

```powershell
python scripts/preparar_fondos.py     # requiere pillow + numpy
```

Reconstruye el canal alfa (los PNG de origen traen el damero de "fondo transparente"
horneado), recorta, calcula el acento y la opacidad de cada imagen y escribe
`nicegui_ui/static/fondos/` (+ `mini/` para la banda y el selector). Imprime las líneas
de `tema.TEMAS` listas para pegar: esos valores se derivan de las imágenes, no se eligen
a ojo.

### Apagado programado

La vista **Apagado** (`/apagado`) programa el apagado o reinicio del PC. Es una utilidad
**de escritorio local** —como el reloj y los logins—: no pasa por la API, envuelve
`shutdown.exe`. El temporizador lo mantiene **Windows**, así que sobrevive a que cierres
la UI y se cancela desde cualquier parte. Ofrece atajos (15…240 min), minutos a medida,
una hora concreta (`HH:MM`, que salta a mañana si ya pasó) y el flag `/f`. Hibernar y
cerrar sesión son **inmediatos**: `shutdown.exe` no admite retardo para ellos.

Fuera de Windows —o dentro del contenedor, donde apagaría el contenedor y no el PC— la
página se deshabilita con un aviso. Equivalente por consola:

```powershell
.\scripts\apagar.ps1 -Minutos 45
.\scripts\apagar.ps1 -Hora 23:30 -Accion reiniciar
.\scripts\apagar.ps1 -Cancelar
```

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

# Todo lo que verifica el CI, en el mismo orden (correr ANTES de commitear):
.\scripts\verificar.ps1
.\scripts\verificar.ps1 -Rapido       # salta el arranque del stack (lo más lento)
```

### Lo que verifica el CI

`.github/workflows/ci.yml` va de rápido a lento, en cascada — no se gastan minutos de build en
algo que un lint de segundos ya iba a rechazar:

| Job | Qué comprueba |
|---|---|
| `lint` | `ruff check` (imports muertos, orden, modismos obsoletos). Config en `pyproject.toml` |
| `test` | pytest en SQLite con **`--cov-fail-under=80`**: la cobertura es condición de fallo, no un número decorativo |
| `test-postgres` | la misma suite contra **Postgres 18 real** (servicio de Actions), con `-rs` para que los saltados sean visibles |
| `deploy-check` | `manage.py check --deploy --fail-level WARNING` con `DEBUG=False` + `SECURE_HTTPS=True` y una `SECRET_KEY` efímera |
| `build` | construye ambas imágenes **y levanta el stack**, esperando a que los tres servicios queden `healthy` |

El último es el que importa: un CI que solo comprueba que la imagen *compila* da falsa
seguridad, porque los fallos reales (migraciones, conexión a la base, token de la UI) aparecen
al **arrancar**.

`.githooks/pre-commit` corre `ruff` sobre los `.py` del commit y `hadolint` sobre los
Dockerfiles tocados, filtrando por archivos: un commit de documentación no espera a que
arranquen tres contenedores. Se activa una sola vez con `git config core.hooksPath .githooks`.

> `ruff format` **no** está en el CI: reformatearía 58 de 102 archivos, y eso es un cambio de
> estilo global que merece su propio commit, no colarse en una refactorización de
> infraestructura.

224 tests en total: backend (Django + DRF, incl. dashboard/racha de tareas, PDFs de
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
