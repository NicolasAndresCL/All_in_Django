# 🧩 All in Django — API Django/DRF + UI NiceGUI con IaC de punta a punta

[![CI](https://github.com/NicolasAndresCL/All_in_Django/actions/workflows/ci.yml/badge.svg)](https://github.com/NicolasAndresCL/All_in_Django/actions/workflows/ci.yml)
![Versión](https://img.shields.io/badge/versi%C3%B3n-2.2.0-blue)
![Python](https://img.shields.io/badge/python-3.14-3776AB)

| | |
|---|---|
| **Versión** | 2.2.0 |
| **Fecha** | 26 de octubre de 2026 |
| **Autor** | [Nicolás Andrés Cano Leal](#autor) |

Versión **Django + Django REST Framework** del proyecto `all_in_one` (que era 100% Streamlit).
Backend con API REST + Django Admin, configuración tipada con **pydantic-settings**,
metodología pythonic (clases, servicios, excepciones claras, logging, callbacks) y
tests con **pytest-django**.

## Stack

Python 3.14 · Django 6 · DRF · pydantic-settings · **pandas · NumPy · scikit-learn · seaborn** ·
openpyxl · requests/beautifulsoup4 ·
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
│   ├── tareas/              # Registro (+ resumen pandas, analitica sklearn, informe seaborn)
│   ├── notas/               # Nota (+ exportar md/txt)
│   ├── tv/                  # scraper de canales (solo lectura)
│   └── extras/              # commands: importar_all_in_one, reloj, login_menu
├── nicegui_ui/             # UI NiceGUI (cliente HTTP de la API) — ver su README
│   ├── main.py  layout.py  tema.py  plotly_tema.py  api_client.py  run_ui.py  run_app.bat
│   ├── views/               # una vista por dominio (tareas: dashboard con 6 gráficos Plotly)
│   ├── Dockerfile           # imagen de la UI
│   └── tests/               # cliente, charts, gantt, tema, páginas, interacción y visual (Playwright)
├── Dockerfile  docker/entrypoint.sh  docker-compose.yml  .dockerignore  .env.docker.example
├── docker-compose.deploy.yml # CD: imágenes de GHCR, sin build
├── compose.traefik.yml      # override del VPS: detrás de un Traefik existente, 0 puertos publicados
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
| Respaldos | `scripts/respaldar_bd.ps1`, `scripts/restaurar_bd.ps1` | dumps `-Fc` verificados del volumen (a mano) |
| Respaldo programado | `Jenkinsfile.respaldo` | job nocturno que **restaura** el dump y compara el censo |
| CI | `.github/workflows/ci.yml` | lint → tests/cobertura + Postgres real + hardening → build, arranque **y pruebas HTTP** |
| Pruebas de API | `postman/` + `docker-compose.test.yml` + `scripts/probar_api.ps1` | stack efímero + colección Postman (Newman) |
| Publicación | `.github/workflows/docker-publish.yml` | push a GHCR en tags `v*` (semver **sin la `v`** + sha, **no** `latest`) |
| Releases | `.github/workflows/release.yml` + `CHANGELOG.md` | GitHub Release por tag, con las notas de su sección del CHANGELOG |
| **CD** | `Jenkinsfile` + `docker-compose.deploy.yml` | deploy de GHCR por compose, con respaldo previo y **rollback** |
| **VPS** | `compose.traefik.yml` + `docker-compose.deploy.yml` | despliegue detrás de un Traefik existente: 0 puertos publicados, basic auth, `mem_limit` ([detalle](#detrás-de-un-traefik-existente-vps)) |
| Nube | `infra/terraform/` (AWS EC2 + RDS Postgres 18) | infra en la nube (skeleton) |
| Kubernetes | `infra/helm/all-in-django/` | chart (API/UI/Postgres 18/Ingress) |

### Docker Compose (forma recomendada de levantar todo)

```bash
cp .env.docker.example .env.docker   # SECRET_KEY, POSTGRES_* y API_TOKEN son OBLIGATORIOS
docker volume create all_in_django_pgdata        # UNA vez por máquina: el volumen es external
docker compose --env-file .env.docker up -d      # db (healthy) → api (migra) → ui
```

> Se pasa `--env-file .env.docker` para que Compose no lea el `.env` de Django (su `SECRET_KEY`
> con `$` provoca warnings de interpolación inofensivos).
>
> ⚠️ **El entorno del shell manda sobre `--env-file`.** Si en esa misma consola corrió antes
> `scripts/verificar.ps1` (o cualquier script que exporte `SECRET_KEY`), Compose usa la del
> shell y la API arranca con una clave que no está en ningún archivo, sin aviso. Pasó el
> 2026-09-02 y el stack corrió 14 días así. `verificar.ps1` ya limpia la variable al terminar;
> antes de un `up`, `$env:SECRET_KEY` debe estar vacío.

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

Los datos viven en el volumen **`all_in_django_pgdata`**, declarado **`external: true`** en
los dos compose (desde el 2026-09-19). Eso cambia quién puede borrarlo:

| Operación | Volumen nombrado normal | Volumen `external` |
|---|---|---|
| `docker compose down` | sobrevive | sobrevive |
| `docker compose down -v` | **se borra** | sobrevive (Compose no lo gestiona) |
| `docker volume rm` / *Clean data* de Docker Desktop | se borra | se borra |

El precio es un paso único por máquina: `docker volume create all_in_django_pgdata`. Sin él,
`up` falla ruidoso con *external volume not found* en vez de crear uno vacío y levantar la API
contra una base en blanco. En el host de Jenkins ya existe (es el mismo volumen que usa
`docker-compose.deploy.yml`).

Verificado el 2026-09-19 con un `down` → `up` real: mismas 17 tablas, mismos conteos fila a
fila (`COUNT(*)`), mismo OID de base. Además del dump lógico, quedó un **respaldo físico del
volumen** (1.368 ficheros, 8,1 MB) tomado con la base parada:

```powershell
docker compose --env-file .env.docker down          # la base tiene que estar parada
docker run --rm -v all_in_django_pgdata:/datos:ro -v C:\dev\backups:/respaldo alpine `
    sh -c "tar -czf /respaldo/all_in_django_pgdata_$(Get-Date -f yyyy-MM-dd).tgz -C /datos ."
docker compose --env-file .env.docker up -d
```

El `.tgz` solo sirve para la **misma versión mayor** de Postgres; para cualquier otra cosa, el
dump `-Fc` de abajo.

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

**Flujo**: versión subida en `config/settings.py`, `Chart.yaml` y README, y su sección en
`CHANGELOG.md` → push con el CI en verde → `git tag -a vX.Y.Z -m "..."` + `git push origin vX.Y.Z`
→ Actions publica `all-in-django-{api,ui}:X.Y.Z` a GHCR (**sin la `v`**) y `release.yml` crea la
GitHub Release (falla sin publicar si el tag no coincide con la versión o falta la sección) →
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
IMAGE_TAG=2.2.0 docker compose --env-file .env.docker -f docker-compose.deploy.yml pull
IMAGE_TAG=2.2.0 docker compose --env-file .env.docker -f docker-compose.deploy.yml up -d
```

> Ya no se pasa `-p`: el nombre de proyecto (`all_in_django`) está fijado con `name:` dentro de
> ambos compose. Antes, desarrollo usaba `all_in_django` (por el directorio) y este pipeline
> `-p all-in-django`: **dos stacks distintos para la misma app**, y el healthcheck buscaba un
> contenedor `all-in-django-api-1` que no existía.

**Prerequisitos en Jenkins** (ya montados en la máquina de desarrollo):

| Requisito | Por qué | Estado |
|---|---|---|
| Imagen de Jenkins **con cliente de Docker** | `jenkins/jenkins` no trae el binario `docker`: sin él, cada `sh 'docker …'` muere con `docker: not found`, aunque el socket esté montado | `jenkins/Dockerfile` |
| `/var/run/docker.sock` montado | Despliega en el mismo daemon | ya estaba |
| Credencial **Secret file `all-in-django-env`** | Contenido de `.env.docker`. El pipeline la materializa al workspace y la borra al terminar | `init.groovy.d/10-…` |
| Job **`all-in-django-cd`** (Pipeline desde SCM) | El Jenkinsfile viaja con el código | `init.groovy.d/20-…` |
| Credencial `ghcr-credentials` | **Solo** si los paquetes GHCR son privados; marcar entonces `GHCR_PRIVATE` | pendiente si aplica |

> Credenciales y jobs se crean con scripts Groovy de arranque, no a mano. Es la única
> vía programática para una credencial: su contenido se cifra con la clave maestra de
> Jenkins, así que escribir `credentials.xml` desde fuera no funciona. Detalle en
> `jenkins/README.md`.

> **Nota (`latest`)**: Actions publica `{{version}}`/`{{major}}.{{minor}}`/`sha` pero **no
> `latest`** (`flavor: latest=false`; hasta la 1.0.0 sí lo publicaba, por el default de
> `metadata-action`, y ese `latest` viejo sigue en GHCR apuntando a la 1.0.0) — pasa el semver
> publicado en `IMAGE_TAG`. El pipeline **aborta** si recibe
> `latest` o un valor vacío.

#### Ensayar el pipeline sin publicar nada

`REGISTRY` es un parámetro del job (por defecto `ghcr.io`). Apuntándolo a un registry
local se ejercita el pipeline **entero** —pull, deploy, healthcheck, rollback— sin
subir una imagen a ningún sitio. Una tubería que solo se puede probar publicando no se
ensaya nunca.

```bash
docker run -d --name registry-local -p 5000:5000 --restart unless-stopped registry:2
docker tag all_in_django-api:latest localhost:5000/nicolasandrescl/all-in-django-api:2.2.0
docker tag all_in_django-ui:latest  localhost:5000/nicolasandrescl/all-in-django-ui:2.2.0
docker push localhost:5000/nicolasandrescl/all-in-django-api:2.2.0
docker push localhost:5000/nicolasandrescl/all-in-django-ui:2.2.0
# y lanzar el job con IMAGE_TAG=2.2.0  REGISTRY=localhost:5000
```

Así se validó el pipeline de verdad, y así se destaparon dos fallos que **no se ven
leyendo el Jenkinsfile** (ambos ya corregidos): en un pipeline declarativo los bloques
`post` corren en orden `always` → `failure`/`success` → `cleanup`, de modo que limpiar
en `always` borraba el respaldo antes de archivarlo y el `.env.docker` antes de que el
rollback pudiera usarlo — el rollback fallaba justo cuando hacía falta.

**Para comprobar que el rollback funciona hay que provocar un fallo**, no confiar en
que el código parece correcto: se publica una imagen que arranque pero no responda al
healthcheck, se despliega, y se verifica que el servicio vuelve solo a la versión
anterior.

### Detrás de un Traefik existente (VPS)

Para un servidor que **ya tiene un Traefik** con Let's Encrypt en el 80/443 (el VPS compartido con
n8n), `compose.traefik.yml` se aplica **encima** de `docker-compose.deploy.yml`: las imágenes salen de
GHCR (en el servidor no se construye nada) y el stack queda detrás de ese Traefik sin tocar su
configuración.

| Qué cambia respecto del compose de despliegue | Por qué |
|---|---|
| **Ningún puerto publicado** | Docker se salta firewalld/ufw con los puertos publicados |
| **Solo la UI entra a la red de Traefik**, con basic auth | La UI es cliente **servidor-a-servidor** de la API (`requests` desde el proceso de NiceGUI: el navegador nunca la llama) y no tiene login propio |
| API y Postgres en `all_in_django-net` | No son alcanzables desde Traefik: `/admin/` y `/api/token/` no quedan en internet |
| `mem_limit` 160 / 512 / 320 MiB (db / api / ui) | VPS compartido. Se ajustan con `DB_MEM_LIMIT`, `API_MEM_LIMIT` y `UI_MEM_LIMIT` en el `.env` |
| 1 worker de gunicorn y Postgres con `shared_buffers=32MB` | Cada worker carga pandas + scikit-learn + seaborn |
| Un único `.env` (se anula `env_file: .env.docker`) | El servidor no tiene `.env.docker` |

Variables del `.env` además de las de `.env.docker.example` (en **negrita** las obligatorias):

| Variable | Para qué |
|---|---|
| `COMPOSE_PATH_SEPARATOR=:` y `COMPOSE_FILE=docker-compose.deploy.yml:compose.traefik.yml` | Un `docker compose up` a secas aplica siempre el override, nunca el compose base con puertos |
| **`IMAGE_TAG`** | Semver publicado en GHCR, sin `v` (p. ej. `2.2.0`) |
| **`ALL_IN_DJANGO_HOST`**, **`TRAEFIK_NETWORK`** | Nombre público y red de Docker donde vive el Traefik (`docker network ls`) |
| **`ALL_IN_DJANGO_BASIC_AUTH`** | `usuario:hash` (`openssl passwd -apr1`) **entre comillas simples**, para que Compose no interprete los `$` del hash |
| **`UI_STORAGE_SECRET`** | Firma la cookie de sesión de NiceGUI (`openssl rand -hex 24`) |
| `ALLOWED_HOSTS` | Debe incluir `api` (el Host con el que llama la UI) y `localhost` (el del healthcheck); el default del override ya los trae |
| `SECURE_HTTPS` | Déjalo en **`False`** (ver el aviso de abajo) |

`SECRET_KEY`, `POSTGRES_*` y `API_TOKEN` son los de siempre. `DATABASE_URL` no se define: el compose la
arma con `POSTGRES_*`.

```bash
git clone --branch v2.2.0 https://github.com/NicolasAndresCL/All_in_Django.git /opt/all_in_django
cd /opt/all_in_django
docker volume create all_in_django_pgdata          # UNA vez: el volumen es external
# crear el .env (modo 600) con las variables de arriba; API_TOKEN provisional hasta el paso 2
docker compose config | grep -c published          # debe dar 0
docker compose pull
docker compose up -d --wait db api                 # 1. base y API (migra sola)
docker compose exec -T api python manage.py createsuperuser --noinput --username nico --email nico@example.invalid
docker compose exec -T api python manage.py drf_create_token nico   # 2. su salida es el API_TOKEN del .env
docker compose up -d --wait                        # 3. ahora la UI, con el token ya puesto
```

Para actualizar: `git fetch --tags && git checkout vX.Y.Z`, el `IMAGE_TAG` nuevo en el `.env`, `pull` y
`up -d --wait`, con un `pg_dump -Fc` antes: el entrypoint migra en cada arranque y volver a una imagen
vieja tras una migración nueva puede fallar. **`docker compose down` conserva los datos** (el volumen es
`external`); **`docker volume rm all_in_django_pgdata` los borra**.

> **Ojo con `SECURE_HTTPS`:** en este despliegue debe quedar en `False`. La UI llama a la API por
> `http://api:8000` (red interna, sin `X-Forwarded-Proto`) y, con `SECURE_SSL_REDIRECT`, Django contesta
> 301 a `https://api:8000`, donde gunicorn no habla TLS: la UI se queda sin API **con los healthchecks en
> verde**. Solo tendría sentido activarlo si la API se expusiera por su cuenta detrás de TLS y la UI
> dejara de llamarla por HTTP interno.

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
- **Helm**: el chart despliega también la **observabilidad** (`METRICS_TOKEN` y `API_TOKEN` en
  el Secret, `LOG_FORMATO`/`PROMETHEUS_MULTIPROC_DIR` en el ConfigMap, un `emptyDir` para las
  métricas multiproceso y anotaciones `prometheus.io/*`). Se había construido solo para
  Compose, así que un `helm install` arrancaba con las métricas mintiendo y los logs en texto
  plano, con los pods `Running` y las probes en verde. **Las anotaciones no llevan
  credenciales**: como `/metrics` exige bearer, el job de Prometheus necesita además el token
  o recibirá 401 (ver el README del chart). `test_paridad_infra.py` falla si una variable vive
  en un solo entorno.
- **Terraform**: el RDS lleva `skip_final_snapshot = false` con `final_snapshot_identifier`,
  `backup_retention_period` (7 días por defecto) y `deletion_protection`. Antes un `destroy`
  se llevaba la instancia **sin dejar copia**.
- **Terraform**: `image_tag` **no tiene default y rechaza `latest`** (la misma regla que el
  Jenkinsfile y el chart: GHCR nunca lo publica y el `docker compose pull` del cloud-init
  moría en la primera EC2 sin más rastro que su log). Y el cloud-init **da de alta el
  `api_token` en la base** y se lo pasa a la UI: sin él, el stack levantaba `healthy` con la
  UI dando 401 en cada vista — el falso positivo que Compose corta con `${API_TOKEN:?}`.
- **Terraform se prueba sin cuenta de AWS**: `terraform test` con proveedores simulados
  (`tests/infra.tftest.hcl`) afirma que el RDS es privado y solo accesible desde la EC2,
  que el cloud-init inyecta lo que el stack necesita y que las validaciones de entrada
  abortan en el `plan`. Corre en el CI (job `terraform`) y en `verificar.ps1`. Ver el
  [README de Terraform](infra/terraform/README.md#pruebas-sin-credenciales-terraform-test).

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
Los contadores viven en el **cache compartido** (`DatabaseCache`), así que el límite es el
mismo con uno o con N workers de gunicorn.

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
| `/api/tareas/analitica/` | GET | **scikit-learn**: tendencia semanal (`LinearRegression`) y días atípicos (`IsolationForest`) · `?proyecto=` |
| `/api/tareas/informe/` | GET | **PDF con gráficos seaborn**: KPIs, tendencia, horas por proyecto, mapa de calor y atípicos · `?proyecto=` |
| `/api/notas/` | CRUD | |
| `/api/notas/{id}/exportar/?fmt=md\|txt` | GET | descarga la nota |
| `/api/tv/canales/?buscar=` | GET | canales (scraping, cache 1h) |
| `/api/<recurso>/exportar/?formato=excel\|pdf` | GET | export en clases/turnos/tareas |
| `/api/schema/` | GET | esquema **OpenAPI 3** generado del código (drf-spectacular) |
| `/api/schema/swagger-ui/` | GET | visor interactivo del esquema (pide sesión de admin) |
| `/metrics` | GET | métricas Prometheus. **No público**: `Authorization: Bearer <METRICS_TOKEN>` |

### El contrato: esquema OpenAPI

El esquema lo genera **drf-spectacular** a partir de los serializers y de las anotaciones
`@extend_schema`, así que no puede quedarse desfasado como una tabla escrita a mano. Las
acciones que devuelven archivos (`imprimir`, `exportar`, `notas/…/exportar`) van anotadas en
[`core/openapi.py`](core/openapi.py): sin eso el esquema declararía `application/json` para un
PDF, que es peor que no documentarlo.

```powershell
python manage.py spectacular --validate --fail-on-warn --file schema.yml
```

El esquema **no es público**: hereda `IsAuthenticated` como el resto de `/api/`. Se consulta
con token o con sesión de admin (para el Swagger UI, entra antes en `/admin/`).

### Probar la API con Postman

La suite de pytest usa `force_authenticate`: **nunca atraviesa** gunicorn, WhiteNoise, el
middleware, la autenticación por token real ni el rate limiting. La colección de `postman/`
sí: 79 peticiones y ~183 aserciones contra una API de verdad.

```powershell
.\scripts\probar_api.ps1                              # levanta, prueba y limpia (~17 s)
.\scripts\probar_api.ps1 -Carpeta '04 - Registro de tareas'
.\scripts\probar_api.ps1 -Conservar -Informe .\newman.json   # para depurar un fallo
```

El script levanta [`docker-compose.test.yml`](docker-compose.test.yml) — un stack **aparte**,
con base vacía, puertos altos (8010/5434) y **sin volumen** — crea un usuario de pruebas y
corre la colección con Newman (vía `npx`, no hace falta instalarlo). **Tus datos no se tocan
en ningún momento**: el stack de pruebas ni siquiera monta `all_in_django_pgdata`.

| Archivo | Qué es |
|---|---|
| `postman/all_in_django.postman_collection.json` | la colección (v2.1.0). **Fuente de verdad**, versionada |
| `postman/local.postman_environment.json` | plantilla de entorno: `base_url`, `username`, `password`. Sin secretos |
| `postman/fixtures/turnos_ejemplo.csv` | archivo de ejemplo para `turnos-equipo/importar/` |

Las carpetas se ejecutan **en orden** y comparten variables (`token`, ids): la 00 obtiene el
token, la 98 borra lo creado y la 99 va al final porque **agota el rate limit** de
`/api/token/`. Además de los caminos felices, se afirman los infelices: 401 sin token, 400 por
`dia` fuera de los choices, 405, y que los errores de dominio conserven la forma
`{"error", "tipo"}`.

**A mano, en la app de Postman**: importa la colección y el entorno, rellena `username` y
`password`, y usa el Runner. Una limitación conocida: Postman no importa rutas de archivos
locales, así que en la petición *Importar CSV* hay que volver a seleccionar
`postman/fixtures/turnos_ejemplo.csv`.

> Si la corres contra un entorno con datos reales, usa solo las carpetas de lectura. Las de
> escritura marcan todo lo que crean (`POSTMAN-SMOKE`, semanas de 2099) y lo borran al final,
> pero un fallo a medio camino deja residuos.

## Ciencia de datos (pandas · NumPy · scikit-learn · seaborn)

El módulo de **Registro de Tareas** pasa de "sumar en bucles" a una capa de datos declarativa.
Todo parte de **un solo `DataFrame`** (`apps/tareas/services.registros_a_frame`, que con un
QuerySet usa `values_list` y no instancia un modelo por fila) y lo consumen tres piezas:

| Pieza | Librería | Qué hace |
|---|---|---|
| `services.calcular_resumen` → `/resumen/` | **pandas** + **NumPy** | cada serie del dashboard es un `groupby(...).sum()` encadenado; la racha se vectoriza con `np.diff` |
| `analitica.py` → `/analitica/` | **scikit-learn** | `LinearRegression` sobre las horas por semana (pendiente, R², proyección) y `Pipeline(StandardScaler → IsolationForest)` sobre los días |
| `informe.py` → `/informe/` | **seaborn** (`seaborn.objects`) + fpdf2 | PDF con gráficos estáticos renderizados en el servidor |

La importación de LiveOps (`apps/liveops/services.preparar_turnos_equipo`) también dejó
`iterrows()`: cada validación es una máscara booleana y los errores salen de una tabla
condición → mensaje con `np.select`.

**Cómo se comprobó que la refactorización no cambia nada.** Además de los tests de siempre,
las dos funciones se compararon contra su versión anterior (sacada de `git`) con datos
aleatorios: 300 conjuntos para el resumen (297 idénticos al bit; los 3 restantes difieren en
una centésima por redondear un `.xx5` exacto —pandas suma por pares, `sum()` en secuencia—) y
400 DataFrames con casos límite para la importación. Esa comparación destapó un **bug de la
versión anterior**: con la columna `Fecha` en `datetime64` (lo normal al leer un Excel),
`iterrows()` convertía una celda de agente vacía en `NaT` y se importaba un turno a nombre del
trabajador *"NaT"*. Ahora se reporta como `Fila N: sin agente.` y tiene test de regresión.

**Decisiones del modelo** (medidas sobre la base real: 443 registros, 169 días, 25 semanas):

- **Mínimos de datos** — 4 semanas para la tendencia y 10 días para los atípicos. Por debajo
  la API devuelve `tendencia: null` / `atipicos: []` y la UI explica cuánto falta: una recta
  por dos puntos tiene R² = 1 y no dice nada.
- **Semanas vacías = 0 horas** (se reindexa el rango completo): si se omitieran, una pausa de
  un mes no movería la tendencia.
- **`contamination=0.05`** — con `"auto"` el IsolationForest marcaba **48 de 169 días (28 %)**;
  con el 5 % salen 9. Contrapartida asumida: siempre aparece alguno, así que responde *"¿cuáles
  son mis días más raros?"*, no *"¿hay algo raro?"*. `random_state` fijo para que la lista no
  cambie entre recargas.
- **`motivo`** lo decide el rasgo más desviado (z-score): un día con horas normales pero 9
  registros es raro por los registros, y decir "menos horas de lo habitual" explicaba mal lo
  que vio el modelo.

**Gráficos del informe.** Paleta categórica validada (azul para la serie real, naranja para la
tendencia, leyenda solo con dos series), rampa secuencial de un solo tono en el mapa de calor,
proyectos más allá del 8.º plegados en "Otros" y nombres largos truncados. Se usa
`matplotlib.figure.Figure` directamente, **nunca `pyplot`**: pyplot guarda las figuras en
estado global del proceso y en un worker de gunicorn eso es una fuga (un test mira el registro
de pyplot tras generar un informe, y se comprobó que falla si se reintroduce). Con la base real
tarda ~1,3 s y pesa ~130 KB. La imagen de la API precalienta la caché de fuentes de matplotlib
en el build para que el primer informe no la construya en mitad de una petición.

La UI **no** importa scikit-learn ni seaborn: pide `/analitica/` (tarjetas de tendencia, gráfico
Plotly con la recta y tabla de atípicos) y descarga `/informe/` con el botón *Informe PDF*.

**Coste:** la imagen de la API pasó de 642 MB a **1,04 GB** (scikit-learn, scipy, matplotlib y
seaborn). La de la UI no cambia.

## Observabilidad

Los healthchecks dicen *"el proceso responde"*, no *"la aplicación funciona"*. Este proyecto ya
sufrió la diferencia: el stack entero en `healthy` mientras la UI devolvía **401 en cada vista**
por un token que no correspondía a la base. Eso es lo que la observabilidad ve y un healthcheck no.

**Métricas** — `/metrics` (django-prometheus), **no público**: exige
`Authorization: Bearer <METRICS_TOKEN>`. Con la variable vacía el endpoint responde **404**
(deshabilitado, no abierto), así que olvidarla no publica las métricas por accidente.

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"   # genéralo una vez
# El mismo valor va en .env.docker (METRICS_TOKEN) y en infra/observabilidad/token
```

**Logs** — `LOG_FORMATO=json` (por defecto en contenedor) emite una línea JSON por evento, tanto
en Django como en **gunicorn**. `LOG_FORMATO=texto` mantiene el formato legible en desarrollo.

```json
{"remoto":"172.24.0.1","metodo":"GET","ruta":"/api/","status":"401","duracion_us":"2674"}
{"timestamp":"...","level":"WARNING","name":"django.request","message":"Unauthorized: /api/","status_code":401}
```

**Alertas** — Prometheus va en el compose bajo un *profile*, así que el stack de diario no cambia:

```powershell
docker compose --env-file .env.docker --profile observabilidad up -d
# http://localhost:9090  ->  Status/Targets y Alerts
```

| Alerta | Se dispara cuando |
|---|---|
| `ApiCaida` | Prometheus lleva 1 min sin poder leer `/metrics` |
| `Ratio401Alto` | más del 40% de las respuestas son 401 durante 2 min |
| `Ratio5xxAlto` | más del 5% son 5xx durante 2 min |
| `LatenciaAlta` | el p95 supera 2 s durante 5 min |

El umbral de 401 es alto a propósito: la API rechaza peticiones sin token por diseño, así que lo
anómalo no es que haya 401 sino que sean la mayoría. Comprobado provocando el fallo: con la UI
usando un token inválido, `docker ps` seguía mostrando los cuatro contenedores `healthy` y
`Ratio401Alto` pasó a **FIRING**; al restaurar el token volvió a `inactive`.

> Con varios workers de gunicorn cada proceso lleva sus propios contadores, así que la imagen
> define `PROMETHEUS_MULTIPROC_DIR` y el entrypoint lo vacía en cada arranque. Sin eso, `/metrics`
> devolvería los números de **un** worker al azar.

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

La UI usa el puerto **8501** por defecto y, si está ocupado, salta al siguiente libre. Desde la
2.2.0 es **100 % responsiva** (celular, tablet y escritorio) y su tema por defecto es **Aurora
austral** (ver más abajo); tablas compactas con scroll interno y gráficos Plotly con **pantalla
completa**. Incluye: **impresión PDF** (estudio, laboral, maestro y equipo), **Gantt** semanal
(personal y de equipo), **copiar/basar una semana en otra**, **grilla semanal editable** de turnos
y **autocompletado** de proyecto/tarea. Detalles en [`nicegui_ui/README.md`](nicegui_ui/README.md).

Como la API exige token, la UI necesita **`API_TOKEN`** (variable de entorno o
`nicegui_ui/.env`). Créalo con `python manage.py drf_create_token <usuario>`.

La imagen de la UI fija `TZ=America/Santiago`: «hoy» y «la semana actual» los calcula la UI con
`date.today()` (calendario, LiveOps y tareas) y un contenedor corre en UTC, así que pasadas las
20-21 h en Chile ofrecía el día siguiente. La API no lo necesita: Django fija `TZ` desde
`TIME_ZONE` al cargar `settings`.

Si algo falla, la vista de Inicio **dice qué falla**, no siempre lo mismo: falta de token,
token rechazado (típico cuando es de otra base de datos: se creó en SQLite y la API ya
corre sobre Postgres), **429 por rate limit** —que no es un problema de credenciales— o la
API caída. Un token que aparece de pronto en el entorno se recoge al recargar la página,
sin reiniciar la UI.

### Identidad visual y temas

La UI tiene **dos estilos** que comparten estructura, y un **selector de tema** en la esquina
superior derecha para elegir entre ellos. La elección se guarda en `app.storage.user`, es decir
**por navegador**, y sobrevive a reiniciar la UI.

| Opción del selector | Estilo | Qué se ve |
|---|---|---|
| **Aurora austral** (por defecto desde la 2.2.0) | `aurora` | Cielo nocturno del sur con auroras en movimiento, vidrio esmerilado, cifras en degradado |
| Uno de los **16 personajes** | `cubierta` | El personaje como marca de agua con su aura, madera de cubierta y su color en toda la interfaz |
| **Auto** | `cubierta` | El personaje propio de cada página (Nami en Calendario, Zoro en Tareas…) |

#### Aurora austral

Un cielo nocturno del extremo sur de Chile, donde la aurora austral se deja ver en invierno:

- **Cortinas de aurora** verde → violeta → rosa (`body::after`): tres elipses difuminadas que se
  deforman despacio en un ciclo de 28 s. Solo se anima `transform` sobre una capa ya difuminada,
  que el navegador mueve en el compositor sin repintar: es barato también en un celular.
- **Estrellas** que titilan (`body::before`), más densas arriba y que se apagan hacia abajo.
- El fondo es **azul noche** (`#050814`), no negro: sobre negro puro el vidrio no se nota.
- **Vidrio** en tarjetas, tablas y campos (velo azul noche al 84 %), con un reflejo verde-violeta
  en la esquina y un filo de luz arriba; al pasar el ratón se encienden. El desenfoque
  (`backdrop-filter`) queda solo en la barra superior y el menú: con el cielo animado detrás, el
  navegador tendría que re-desenfocar cada tarjeta en cada fotograma (medido: una captura de página
  completa a 360 px no terminaba en 30 s).
- Barra superior de vidrio con un **filo de 2 px en degradado de aurora**; menú lateral a juego.
- **Cifras en degradado** verde → violeta (los dos extremos superan 4,5:1 sobre la superficie).
- Todo **procedural** (gradientes CSS): 0 KB de imágenes nuevas.
- Con `prefers-reduced-motion: reduce` el cielo queda quieto; con `forced-colors` las cifras vuelven
  a color de sistema.

**Contraste medido** (WCAG 2.1, sobre la superficie de las tarjetas `#0c1222`): texto principal
15,5:1, secundario 9,8:1, ticks 6,1:1, acento verde 11,8:1, violeta 6,9:1, rosa 7,1:1. Los
**botones primarios** llevan tinta oscura en todos los temas: el blanco sobre los acentos daba
1,3–3,4:1 (suspende AA) y la tinta oscura da 5,6–14:1.

¿Por qué un tema nuevo por defecto y no reemplazar los personajes? Los personajes se quedan: son
identidad y el selector los sigue ofreciendo tal cual. Pero en un celular la ilustración a 84 vh
compite con datos que ya tienen poco espacio; el cielo da la misma sensación de lugar sin ocupar
nada.

#### Estilo cubierta (los 16 personajes)

Cada página tiene **un personaje de fondo y un color de aura propios** en modo Auto. El reparto es
semántico: Nami (la navegante) en Calendario, Jinbe (el timonel) en LiveOps, Zoro en Tareas, Robin
(la arqueóloga) en Notas, Brook en TV y el sombrero colgado en Apagado. La portada abre con la
tripulación al completo (en ambos estilos).

El personaje se dibuja como marca de agua a plena presencia —se le ve la cara— y el aura
sale de un `drop-shadow` calculado sobre su propia silueta, no de un rectángulo de color.
La **opacidad se calibra por personaje** midiendo su brillo medio: Brook, de frac negro,
necesita más del doble que un emblema claro para leerse igual de presente.

El color del personaje no se queda en el fondo: **tiñe toda la interfaz**. La barra
superior y el menú lateral arrancan del acento y se apagan a negro antes de la mitad; las
**tarjetas** llevan ese mismo degradado, borde y realce superior (y se encienden al pasar
el ratón); tablas, separadores, gráficos y el menú del selector siguen el mismo color. Las
cifras de las métricas van en `aid-cifra`, que pinta con el acento activo (no `text-primary`:
es una utilidad `!important` de Quasar y el degradado del estilo aurora no podría pisarla).

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
| Clases **Tailwind** | Composición, espaciado y **responsividad** (`grid-cols-1 md:grid-cols-2 2xl:grid-cols-3`) | vistas y `layout.py` (`REJILLA_*`) |
| `ui.add_head_html(..., shared=True)` | SOLO lo inexpresable en Python: `body::before/::after` (marca de agua, estrellas, aurora), `@keyframes`, `:fullscreen`, `@media (hover: none)` y el estilo interno de Plotly | `tema.instalar()` |
| Plantilla Plotly `aid` | Tinta, rejilla, leyenda, paleta y márgenes de TODOS los gráficos | `plotly_tema.py` |

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
a ojo. La entrada `aurora` no sale de aquí (no tiene imagen): se mantiene a mano en
`tema.py`, y el test que exige un tema por cada PNG la ignora.

### Responsividad y gráficos (2.2.0)

La UI se usa desde el celular y la tablet, así que se auditó con Playwright sobre el stack real
(datos reales: 679 tareas, 38 proyectos) midiendo cada gráfico en cinco anchos. **Ancho de cada
gráfico del dashboard de Tareas**, antes y después:

| Ancho de pantalla | Antes | Después | Columnas |
|---|---|---|---|
| 360 px (móvil) | 104 px | **318 px** | 2 → 1 |
| 412 px (móvil) | 130 px | **370 px** | 2 → 1 |
| 768 px (tablet) | 308 px | **334 px** | 2 → 2 (drawer cerrado) |
| 1280 px (portátil) | 414 px | **432 px** | 2 → 2 |
| 1920 px (escritorio) | 516 px | **481 px** ×3 | 2 → 3 (contenido hasta 1600 px) |

| Hallazgo | Solución |
|---|---|
| `ui.grid(columns=2)` fijo: 104 px por gráfico a 360 px | `rejilla_graficos()`: 1 / 2 (`md`) / 3 (`2xl`) columnas |
| Barra de Plotly de 11 iconos partida en 2-3 filas; el botón de pantalla completa la pisaba | 4 botones, solo al pasar el ratón, oculta en táctil y < 640 px; pantalla completa en la cabecera de la tarjeta |
| Gantt con 20 ticks fijos (ilegibles < 420 px) y leyenda vertical comiendo ⅓ del ancho | Eje de hora real (ticks adaptativos), leyenda horizontal, días abreviados, siempre los 7 días |
| Colorbar redundante y nombres largos en «Esfuerzo» | Una serie, un color; nombres truncados con el completo en el tooltip; cola en «Otros» |
| Alturas fijas en px (tiras altas y flacas en móvil) | `aid-alto-s/m/l/xl` con `clamp()` sobre `vw` |
| El svg no seguía al contenedor al cerrar el drawer | Lo resuelve el `ResizeObserver` del componente `ui.plotly` (verificado: 646 = 646 px tras cerrar) |
| Gantt sin plantilla (ejes en `#2a3f5f` sobre negro); sunburst con cientos de rebanadas | Plantilla `aid` para todos; **treemap** con colas plegadas |
| Drawer abierto como overlay en cada navegación < 1024 px; filas `no-wrap` en LiveOps y Notas | Drawer `show-if-above`; rejillas que apilan en móvil |
| Etiquetas «Sem N» del eje X montadas unas sobre otras a 360 px | Máximo 6 rótulos cortos («S27», siempre la última semana); ejes de fecha en una sola línea. 0 solapes medidos en los 7 gráficos a 360/412/768/1280 px |

Lo que ya estaba bien y se conservó: ningún ancho tenía scroll horizontal de página y ningún
gráfico desbordaba su tarjeta. Los gráficos modernos se eligieron con la skill `dataviz`
(forma según la tarea del dato, paleta validada con su script para fondo oscuro, una serie =
un color, ≤ 7 categorías con color + «Otros»): **treemap** para la distribución y un
**calendario de actividad** (semana × día) en vez del área diaria.

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
  (frena fuerza bruta). Configurable vía `THROTTLE_*`. Los contadores se guardan en el
  **cache**, y el cache es `DatabaseCache` (tabla `django_cache`, creada por migración) **a
  propósito**: el `LocMemCache` que Django usa por defecto es por proceso, así que con los 3
  workers del contenedor el límite efectivo era ~3× el configurado (el 429 llegaba al intento
  15 en vez de al 11) sin que nada diera error. Comprobado por HTTP en la carpeta 99 de la
  colección Postman, que ahora **exige** el 429 en el intento 11.
- **`SECURE_HTTPS=True`** (solo detrás de TLS real) activa: `SECURE_SSL_REDIRECT` (con
  `/healthz/` exento para los healthchecks), HSTS (1 año, subdominios, preload) y cookies
  `Secure` de sesión/CSRF. Con esto `manage.py check --deploy` queda **sin warnings**.
  En local/Compose se deja apagado porque se sirve HTTP plano. **Tampoco con un TLS que solo
  cubra a la UI** (Traefik delante de la UI, ver [Detrás de un Traefik existente](#detrás-de-un-traefik-existente-vps)):
  la UI llama a la API por HTTP interno y el redirect la deja sin API.

## Tests

```powershell
pytest                                  # backend: lógica, modelos, API, servicios, scraper
pytest nicegui_ui/tests                 # UI: cliente + smoke de páginas (HTTP mockeado)
# Cobertura con coverage.py (vía pytest-cov):
pytest --cov=apps --cov=core --cov=nicegui_ui --cov-report=term-missing

# Pruebas HTTP contra una API de verdad (stack efímero; no toca tus datos):
.\scripts\probar_api.ps1

# Todo lo que verifica el CI, en el mismo orden (correr ANTES de commitear):
.\scripts\verificar.ps1
.\scripts\verificar.ps1 -Rapido       # salta los pasos que levantan contenedores (lo más lento)
# El paso de Terraform usa el binario si está en el PATH; si no, la imagen hashicorp/terraform.
# El del override de Traefik (3c) solo usa `docker compose config`: corre también con -Rapido.
```

### Lo que verifica el CI

`.github/workflows/ci.yml` va de rápido a lento, en cascada — no se gastan minutos de build en
algo que un lint de segundos ya iba a rechazar:

| Job | Qué comprueba |
|---|---|
| `lint` | `ruff check` (imports muertos, orden, modismos obsoletos). Config en `pyproject.toml` |
| `test` | pytest en SQLite con **`--cov-fail-under=80`** (la cobertura es condición de fallo, no un número decorativo) y validación del **esquema OpenAPI** con `--fail-on-warn` |
| `test-postgres` | la misma suite contra **Postgres 18 real** (servicio de Actions), con `-rs` para que los saltados sean visibles |
| `deploy-check` | `manage.py check --deploy --fail-level WARNING` con `DEBUG=False` + `SECURE_HTTPS=True` y una `SECRET_KEY` efímera |
| `compose-traefik` | `compose.traefik.yml` sobre `docker-compose.deploy.yml` con `docker compose config` (no levanta nada): resuelve sin `.env.docker`, **0 puertos publicados**, solo la UI en la red de Traefik, todos con `mem_limit` y `SECURE_HTTPS=False` por defecto (`scripts/comprobar_override_traefik.py`, el mismo que usa `verificar.ps1`) |
| `terraform` | `fmt -check`, `init -backend=false`, `validate` y **`terraform test`** con proveedores simulados: RDS privado, token de la UI en el cloud-init, `image_tag` ≠ `latest`. Sin credenciales AWS ni recursos de pago |
| `build` | construye ambas imágenes, **levanta el stack** esperando a que los tres servicios queden `healthy` y le **pasa la colección Postman con Newman** |

El último es el que importa: un CI que solo comprueba que la imagen *compila* da falsa
seguridad, porque los fallos reales (migraciones, conexión a la base, token de la UI) aparecen
al **arrancar** — y algunos, solo al *usarla*. Por eso el job no se conforma con el
healthcheck: crea un usuario real dentro del contenedor y ejercita la API por HTTP. El
`API_TOKEN` que el job fabrica es un placeholder que no corresponde a ningún token de la base
(basta para que la UI arranque), así que las pruebas piden el suyo por `POST /api/token/`.

`.githooks/pre-commit` corre `ruff` sobre los `.py` del commit y `hadolint` sobre los
Dockerfiles tocados, filtrando por archivos: un commit de documentación no espera a que
arranquen tres contenedores. Se activa una sola vez con `git config core.hooksPath .githooks`.

> `ruff format` **no** está en el CI: reformatearía 58 de 102 archivos, y eso es un cambio de
> estilo global que merece su propio commit, no colarse en una refactorización de
> infraestructura.

284 tests en total (sin contar los de marca `visual`): backend (Django + DRF, incl.
dashboard/racha de tareas, **analítica con scikit-learn e informe seaborn**
—`apps/tareas/test_analitica.py`—, PDFs de
impresión, copiar semanas, **upsert** de turnos y healthcheck `/healthz/`) + **contrato de la
API** (`test_contrato_api.py`: compara el esquema OpenAPI con la colección Postman y falla si
un endpoint no tiene ni una petición que lo visite — es lo que impide que la colección
envejezca en silencio) + **paridad de infraestructura** (`test_paridad_infra.py`: compara las
variables de entorno del compose —y los `ENV` del Dockerfile— con las del chart de Helm y falla
si una existe en un solo entorno; el mismo antídoto contra la deriva silenciosa) + **seguridad**
(`test_seguridad.py`: 401 sin token, obtención/uso del token, rate limit del login con 429,
validación de `SECRET_KEY` débil y el toggle `SECURE_HTTPS`) + **tests unitarios con
`unittest.mock`** (`apps/liveops/test_mock.py`: `guardar_turnos` con el modelo mockeado y la
acción `importar` con los servicios mockeados, sin BD ni archivos) + cliente de la UI (api_client
—incl. que sigue **todas** las páginas de la API y envía el header `Authorization: Token`—) +
**smoke de las 6 páginas NiceGUI** con **`nicegui.testing.User`** (mock HTTP vía `responses`,
incl. casos 401/API caída) + **interacción de la UI** (`test_interaccion.py`: se pulsa el
widget —crear clase, copiar semana, guardar la grilla de 7 días, marcar un día libre, filtrar
tareas, cambiar de tema— y se afirma la petición que sale hacia la API, con su método, ruta y
cuerpo; un `on_click` roto pasa los tests de humo sin despeinarse) y las figuras Plotly
(`charts.py`/`gantt.py`, funciones puras).
Los tests de API usan la fixture **`api`** (conftest raíz): `APIClient` autenticado que además
limpia el cache de throttling entre tests. `test_seguridad.py` afirma también que el backend de
cache **no** es el de por proceso y que los contadores llegan de verdad a la tabla. Los de UI
son `async` (`asyncio_mode=auto`).

### Verificación visual (marca `visual`, fuera del CI)

`nicegui_ui/tests/test_visual.py` levanta la UI de verdad junto a una API falsa y la abre en
**Chromium con Playwright** para **medir**: que el fondo llega a pintarse
(`background-image` del body) y es aurora por defecto, que las cortinas se mueven, que el
header no acaba con el color primario, el **contraste WCAG** del texto sobre las tarjetas y del
botón primario (≥ 4,5:1), que el rebote se **apaga** en hover y con `prefers-reduced-motion`, y
la **responsividad**: a 360, 412 y 768 px los gráficos ocupan ≥ 90 % del ancho útil sin scroll
horizontal, el drawer arranca cerrado en móvil, el svg sigue al contenedor al cerrar el drawer
y la pantalla completa ocupa la ventana. Es lo único que comprueba que el CSS *gana la cascada*: `test_tema.py`
mira la hoja como texto, y un `!important` escrito no prueba que se aplique.

Queda fuera del `pytest` normal y del CI porque exige descargar el navegador (~150 MB):

```powershell
python -m playwright install chromium   # una vez
pytest -m visual                        # también lo corre scripts\verificar.ps1
```

**Cobertura ~83%** (coverage.py); los serializers de turnos, con el upsert, quedan al 100%.
Deps de test en `requirements-dev.txt` (`pytest`, `pytest-asyncio`, `pytest-django`,
`pytest-cov`, `coverage`, `responses`), que **incluye también `nicegui_ui/requirements.txt`**:
los tests de la UI importan `gantt.py`/`charts.py` y las vistas (usan plotly/nicegui) y sin
esas deps la recolección de pytest falla con exit 2. `unittest.mock` es de la stdlib.

Las pruebas HTTP (colección Postman) son el único punto que **no** es Python: las ejecuta
**Newman** vía `npx --yes newman`, así que basta con tener Node instalado; no se añade nada a
`requirements-dev.txt` ni se instala nada global.

## Autor

**Nicolás Andrés Cano Leal**\
Backend Engineer → SRE | Python · Django · Kubernetes · Terraform · CI/CD

- LinkedIn: [linkedin.com/in/nicolasandrescl](https://www.linkedin.com/in/nicolasandrescl/)
- Portafolio: [nicolasandrescl.github.io](https://nicolasandrescl.github.io/)
- Correo: [nicolas.cano.leal@gmail.com](mailto:nicolas.cano.leal@gmail.com)

All in Django v2.2.0 · 26 de octubre de 2026
