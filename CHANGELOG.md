# Changelog

Formato [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y
[versionado semántico](https://semver.org/lang/es/). Cada versión tiene su tag anotado `vX.Y.Z` y su
GitHub Release, que publica `.github/workflows/release.yml` con las notas de esta sección. Las imágenes
de GHCR se publican **sin** la `v`: el tag `v2.0.0` produce `all-in-django-api:2.0.0` y `:2.0`.

## [Sin publicar]

## [2.2.0] — 2026-10-26

La UI se rehace para el celular y la tablet, con un tema nuevo por defecto y gráficos reescritos. La API
no cambia: es un cambio solo de la imagen `all-in-django-ui`.

### Añadido

- **Tema «Aurora austral»** (por defecto): cielo nocturno con cortinas de aurora animadas y estrellas
  (CSS procedural, 0 KB de assets), superficies de vidrio esmerilado, cromo con un filo verde → violeta →
  rosa y cifras en degradado. Contraste AA medido en cada color de texto (11,8:1 el acento). Los 16 temas
  por personaje y el modo Auto siguen en el selector; la elección guardada de cada navegador se respeta.
- **Plantilla Plotly propia** (`nicegui_ui/plotly_tema.py`, plantilla `aid`) aplicada a TODOS los
  gráficos, Gantt incluidos: tinta y rejilla del tema, leyenda horizontal, márgenes automáticos y la
  paleta categórica de la skill `dataviz` validada para fondo oscuro.
- **Calendario de actividad** (heatmap semana × día, últimas 26 semanas) en vez del área diaria, y
  **treemap** con las colas plegadas en «Otras»/«Otros proyectos» en vez del sunburst.
- Pantalla completa con respaldo para iPhone (capa fija cuando Safari no ofrece la Fullscreen API).
- Tests: figuras sin altura fija y con la plantilla, plegado de colas, calendario, colores por entidad,
  CSS responsivo del tema y, en el navegador (`pytest -m visual`), ancho de los gráficos a 360/412/768 px,
  drawer cerrado en móvil, reajuste al cerrar el drawer, contraste del botón primario y pantalla completa.

### Cambiado

- **Rejillas responsivas**: gráficos a 1 columna en móvil, 2 en tablet y 3 en pantallas anchas (antes 2
  fijas: 104 px por gráfico a 360 px); métricas con `auto-fit`; grilla semanal de turnos a 2/4/7
  columnas; canales de TV a 2–6; formularios de LiveOps y Notas apilados en móvil (fuera los `no-wrap`).
- **Alturas que dependen del ancho** (`aid-alto-s/m/l/xl`, `clamp()` sobre `vw`): las figuras ya no fijan
  `height` en píxeles.
- **Drawer responsivo** (`show-if-above`): cerrado por debajo de 1024 px, abierto en escritorio. Antes
  se abría como overlay sobre la página en cada navegación en móvil y tablet.
- Barra de Plotly reducida a descargar/zoom/pan/reset, visible solo al pasar el ratón, oculta en táctil
  y a menos de 640 px (vuelve en pantalla completa). El botón de pantalla completa pasa a la cabecera de
  la tarjeta: ya no se superpone con el título ni con la barra.
- **Gantt** con eje de hora real (ticks adaptativos en vez de 20 fijos), días abreviados, una traza por
  categoría y textos que se ocultan si no caben; el de LiveOps con leyenda horizontal (la vertical se
  comía un tercio del ancho).
- «Esfuerzo por proyecto» y «Actividad por día»: una serie, un color, sin colorbar redundante; nombres
  largos truncados en el eje con el nombre completo en el tooltip; la cola de proyectos en «Otros».
- Contenido hasta 1600 px de ancho (antes 1152).

### Corregido

- Texto de los botones primarios: blanco sobre el acento daba 1,3–3,4:1 en todos los temas (suspende
  AA); ahora tinta oscura, 5,6–14:1. Declarado en la capa CSS `theme` para ganarle al `!important` de
  Quasar.
- Los Gantt no usaban plantilla: ejes y título en el azul marino de Plotly (`#2a3f5f`) sobre negro.
- Se elimina el listener de `fullscreenchange` que llamaba a `window.Plotly`, que no existe (NiceGUI carga
  Plotly como módulo ES): el reajuste lo hace el `ResizeObserver` del componente.

## [2.1.0] — 2026-10-26

Despliegue en un servidor que ya tiene un Traefik (el VPS compartido con n8n). La aplicación no cambia,
salvo la zona horaria de la UI.

### Añadido

- `compose.traefik.yml`: override de `docker-compose.deploy.yml` para desplegar detrás de un Traefik
  existente. No publica ningún puerto; solo la UI entra a la red de Traefik (con basic auth) y la API y
  Postgres quedan en una red propia (`all_in_django-net`); `mem_limit` por servicio ajustable desde el
  `.env` (160 / 512 / 320 MiB); 1 worker de gunicorn; Postgres con memoria acotada; y un único `.env`
  (anula el `env_file: .env.docker` del compose base). Documentado en el README («Detrás de un Traefik
  existente»).
- CI: job `compose-traefik`, que resuelve el override con `docker compose config` (no levanta nada) y
  comprueba con `scripts/comprobar_override_traefik.py` que no publica puertos, que solo la UI toca la red
  de Traefik, que todos los servicios tienen `mem_limit` y que `SECURE_HTTPS` es `False` por defecto. Su
  gemelo local es el paso 3c de `scripts/verificar.ps1`. El job `build` espera ahora a este.

### Cambiado

- Dependabot ya no abre PRs de pip que solo suben la versión mínima (`versioning-strategy:
  increase-if-necessary`). Con `>=` en los requirements el CI ya instala siempre la última versión,
  así que esos PRs no cambiaban lo que se prueba y llegaban cada semana.
- `.dockerignore` excluye `compose.traefik.yml` de la imagen de la API.
- README y `.env.docker.example` avisan de que `SECURE_HTTPS=True` deja a la UI sin API mientras la llame
  por HTTP interno (`http://api:8000`): Django contesta 301 a `https://api:8000`, donde gunicorn no habla
  TLS.

### Corregido

- La imagen de la UI fija `TZ=America/Santiago`. Calendario, LiveOps y Tareas calculan «hoy» y «la semana
  actual» con `date.today()` y el contenedor corría en UTC: pasadas las 20-21 h en Chile ofrecía el día
  siguiente. Afecta también a Docker Desktop y al CD con Jenkins, que usan la misma imagen.

## [2.0.1] — 2026-10-21

Mantenimiento de dependencias, sin cambios visibles. Reemplaza los 13 PRs de Dependabot abiertos
desde agosto (#1 a #13).

### Cambiado

- GitHub Actions a su última versión mayor, que corre sobre Node 24: `checkout` v7, `setup-python` v7,
  `build-push-action` v7, `metadata-action` v6 y `login-action` v4. Incluye `release.yml`, que los PRs
  no cubrían.
- Versiones mínimas de los `requirements` al día con lo que el CI ya instalaba y probaba: DRF 3.18,
  pydantic-settings 2.15, beautifulsoup4 4.15, nicegui 3.18, plotly 7, python-dotenv 1.2.3 y las
  herramientas de test (pytest 9.1, pytest-asyncio 1.4, ruff 0.16.10…).
- Dependabot agrupa las actualizaciones: minor y patch en un solo PR por ecosistema, todas las actions
  juntas y las imágenes base juntas. Solo una versión mayor de pip llega en un PR propio.

## [2.0.0] — 2026-10-21

### ⚠️ Cambio incompatible

- **El volumen de la base es `external`** (`all_in_django_pgdata`) en los dos compose. Ahora `down -v`
  ya no puede borrarlo, pero cada máquina necesita **un paso manual único antes del primer `up`**:

  ```bash
  docker volume create all_in_django_pgdata
  ```

  Sin ese paso, `up` falla con un error explícito en vez de arrancar la API contra una base vacía.
- **Terraform: `image_tag` va sin `v`** (`2.0.0`, no `v2.0.0`), que es como GHCR publica las
  imágenes. La validación rechaza la `v` inicial. El ejemplo anterior (`v1.0.0`) apuntaba a una
  imagen que no existe.

### Añadido

- Observabilidad: métricas Prometheus protegidas con token, logs JSON y alertas ejercitadas en tests.
- Respaldo nocturno que **restaura** el dump y compara el censo real de filas.
- Helm: observabilidad dentro del chart, secretos cifrados con SOPS + age, HTTPS con cert-manager
  (Let's Encrypt staging por defecto) y base gestionada por defecto.
- Terraform: estado remoto en S3 con bloqueo nativo y `terraform test` con proveedores simulados, en el
  CI y en `scripts/verificar.ps1`.
- LiveOps: importación periódica de turnos por la API, con reintentos y verificación; importación
  vectorizada con pandas/NumPy.
- Tareas: capa de ciencia de datos con pandas, scikit-learn y seaborn, con su sección de analítica e
  informe PDF en la UI.
- Tests de UI que pulsan los widgets y miden el CSS.
- `release.yml`: cada tag `vX.Y.Z` publica su GitHub Release con las notas de este archivo.

### Cambiado

- `docker-publish.yml` se dispara **solo** por el push del tag, ya no también al publicar la release.
  Antes cada versión construía y subía las imágenes dos veces.
- GHCR deja de recibir `latest` (`flavor: latest=false`): solo semver y sha, como ya decía la
  documentación.

### Corregido

- Rate limiting: el bloqueo ocurre en el intento 11, no en el 15.
- Respaldo: cuenta filas reales en vez de las estimaciones del planificador.
- Cloud-init de la EC2: hereda las reglas de Compose y Helm.
- `verificar.ps1` borra la `SECRET_KEY` efímera al terminar.
- Tests de interacción de la UI: esperan los `refresh()` que la vista deja en segundo plano. Desde
  nicegui 3.18 el error de esa petición sin simular tumbaba el test en el teardown y contaminaba
  a los siguientes.

## [1.0.0] — 2026-09-01

Primera versión publicada en GHCR (`all-in-django-api` y `all-in-django-ui`).

### Añadido

- Backend Django + DRF con admin, configuración tipada con pydantic-settings, upsert de turnos y grilla
  semanal editable.
- Endurecimiento: autenticación por token, rate limiting y bloque HTTPS opt-in.
- UI migrada de Streamlit a NiceGUI, con temas por personaje e identidad visual por página.
- Stack Docker sobre Postgres 18 con volumen persistente, healthchecks en las imágenes, y respaldo y
  restauración verificados.
- CI en cascada: ruff, pytest con cobertura exigida, Postgres real, `check --deploy` y arranque del stack
  con pruebas HTTP (newman). También Dependabot, plantillas y hook de pre-commit.
- CD con Jenkins: deploy declarativo de las imágenes de GHCR, con respaldo previo y rollback automático.
- IaC: Terraform (EC2 + RDS) y chart de Helm.
- Esquema OpenAPI generado con drf-spectacular y colección Postman que se valida contra un stack efímero.

[Sin publicar]: https://github.com/NicolasAndresCL/All_in_Django/compare/v2.1.0...HEAD
[2.1.0]: https://github.com/NicolasAndresCL/All_in_Django/compare/v2.0.1...v2.1.0
[2.0.1]: https://github.com/NicolasAndresCL/All_in_Django/compare/v2.0.0...v2.0.1
[2.0.0]: https://github.com/NicolasAndresCL/All_in_Django/compare/v1.0.0...v2.0.0
[1.0.0]: https://github.com/NicolasAndresCL/All_in_Django/releases/tag/v1.0.0
