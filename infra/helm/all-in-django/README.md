# Helm chart — All in Django

Despliega la app en Kubernetes: **API** (Django/DRF), **UI** (NiceGUI) y, opcionalmente,
**Postgres** (StatefulSet). Las migraciones corren en un `initContainer` de la API antes de
servir; readiness/liveness apuntan a `/healthz/`.

## Requisitos
- Un clúster (kind/minikube/EKS/…) y `kubectl` apuntándolo.
- Imágenes publicadas en GHCR (workflow `docker-publish.yml`).

## Instalar
```bash
helm lint infra/helm/all-in-django
helm template infra/helm/all-in-django --set secret.secretKey=xxxx   # render local

helm install all-in-django infra/helm/all-in-django \
  --set image.owner=nicolasandrescl \
  --set secret.secretKey="$(python -c 'import secrets;print(secrets.token_urlsafe(50))')"
```

Semilla de datos (una vez):
```bash
kubectl exec deploy/all-in-django-api -- python manage.py loaddata fixtures/datos_sqlite.json
# (requiere que el fixture esté disponible en el pod)
```

Ver la UI:
```bash
kubectl port-forward svc/all-in-django-ui 8501:8501
```

## Valores clave (`values.yaml`)
| Valor | Default | Nota |
|---|---|---|
| `image.owner` | `nicolasandrescl` | owner en GHCR |
| `image.tag` | `""` | vacío → el `appVersion` del Chart. **Nunca `latest`**: el CI no lo publica (solo semver+sha), así que ese default daba `ImagePullBackOff` |
| `secret.secretKey` | *(obligatorio)* | SECRET_KEY de Django |
| `secret.apiToken` | *(obligatorio)* | token con el que la UI llama a la API |
| `secret.metricsToken` | `""` | bearer de `/metrics`; **vacío → el endpoint responde 404** (deshabilitado, no abierto) |
| `observabilidad.scrapeAnnotations` | `true` | anotaciones `prometheus.io/*` en el pod de la API |
| `observabilidad.multiprocDir` | `/tmp/prometheus` | debe coincidir con el `PROMETHEUS_MULTIPROC_DIR` del Dockerfile (hay un test que lo exige) |
| `observabilidad.logFormato` | `json` | `texto` en local; `json` para que un agregador filtre por campo |
| `postgres.enabled` | `true` | `false` → usa base gestionada vía `secret.databaseUrl` |
| `config.ALLOWED_HOSTS` | `*` | ajusta al dominio del Ingress |
| `ingress.enabled` | `false` | activa el Ingress (UI en `/`, API en `/api`,`/admin`,`/static`) |

## Observabilidad

El chart despliega las tres piezas que el stack de Compose ya tenía, porque sin ellas un
`helm install` arranca con **las métricas mintiendo y los logs en texto plano**, y nada lo
avisa: los pods quedan `Running` y las probes en verde.

- **`PROMETHEUS_MULTIPROC_DIR`** + un `emptyDir` montado en esa ruta. Con varios workers de
  gunicorn cada proceso tiene sus contadores en memoria y un scrape cae en uno al azar: la
  mayoría del tráfico desaparece del gráfico sin dar error. El `emptyDir` es lo correcto (los
  ficheros son efímeros y el entrypoint los vacía al arrancar), pero obligó a un arreglo: el
  entrypoint hacía `rm -rf` sobre ese directorio y **`rm -rf` sobre un punto de montaje falla
  con `Resource busy`** → con `set -e`, `CrashLoopBackOff`. Ahora vacía el contenido con
  `find -mindepth 1 -delete`.
- **`LOG_FORMATO=json` / `LOG_LEVEL`** en el ConfigMap.
- **`METRICS_TOKEN`** en el Secret, vacío por defecto.

### El scrape necesita el token, las anotaciones no lo llevan

`prometheus.io/scrape` solo **marca** el pod como scrapeable; el descubrimiento por
anotaciones no transporta credenciales. Como `/metrics` exige `Authorization: Bearer`, un
Prometheus configurado solo con anotaciones recibirá **401**. Hay que darle el token en su
propio job:

```yaml
# En el scrape_config del job kubernetes-pods (o en un ServiceMonitor con bearerTokenSecret)
authorization:
  type: Bearer
  credentials_file: /etc/prometheus/token
```

Es el mismo mecanismo que usa `infra/observabilidad/prometheus.yml` para el stack de Compose.

## Producción
- Prefiere Postgres gestionado (`postgres.enabled=false` + `secret.databaseUrl`) sobre el
  StatefulSet embebido.
- Sirve tras HTTPS (Ingress + cert-manager) y fija `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS`.
- Gestiona `SECRET_KEY`/`DATABASE_URL`/`API_TOKEN`/`METRICS_TOKEN` con un Secret externo
  (SealedSecrets/SOPS), no `--set`.
- `test_paridad_infra.py` falla si una variable existe en el compose y no en el chart (o al
  revés): es lo único que impide que este chart vuelva a quedarse atrás.
