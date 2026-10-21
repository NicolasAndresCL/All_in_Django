# Changelog

Formato [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y
[versionado semántico](https://semver.org/lang/es/). Cada versión tiene su tag anotado `vX.Y.Z` y su
GitHub Release, que publica `.github/workflows/release.yml` con las notas de esta sección. Las imágenes
de GHCR se publican **sin** la `v`: el tag `v2.0.0` produce `all-in-django-api:2.0.0` y `:2.0`.

## [Sin publicar]

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

[Sin publicar]: https://github.com/NicolasAndresCL/All_in_Django/compare/v2.0.0...HEAD
[2.0.0]: https://github.com/NicolasAndresCL/All_in_Django/compare/v1.0.0...v2.0.0
[1.0.0]: https://github.com/NicolasAndresCL/All_in_Django/releases/tag/v1.0.0
