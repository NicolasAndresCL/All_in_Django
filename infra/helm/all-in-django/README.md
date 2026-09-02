# Helm chart — All in Django

Despliega la app en Kubernetes: **API** (Django/DRF) y **UI** (NiceGUI), contra una base
**gestionada** (el RDS de `infra/terraform`); el Postgres embebido en StatefulSet queda como
opción para local (`postgres.enabled=true`). Las migraciones corren en un `initContainer` de la
API antes de servir; readiness/liveness apuntan a `/healthz/`. Los secretos van **cifrados con
SOPS**, y hay HTTPS opcional con **cert-manager**.

## Requisitos
- Un clúster (kind/minikube/EKS/…) y `kubectl` apuntándolo.
- Imágenes publicadas en GHCR (workflow `docker-publish.yml`).
- **`sops`** y **`age`** para los secretos (ver *Secretos*). En Windows:
  `winget install SecretsOPerationS.SOPS FiloSottile.age`.

## Instalar
```bash
helm lint infra/helm/all-in-django

# Render local. Los secretos NO van en --set (ver "Secretos"): salen del archivo cifrado,
# y sops los descifra a un temporal que borra al salir.
sops exec-file infra/helm/secretos/secretos.enc.yaml \
  'helm template all-in-django infra/helm/all-in-django -f {}'

sops exec-file infra/helm/secretos/secretos.enc.yaml \
  'helm upgrade --install all-in-django infra/helm/all-in-django -f {} --set image.owner=nicolasandrescl'
```

`secret.apiToken` es **obligatorio**, igual que el `${API_TOKEN:?}` del compose: sin él la UI
levanta con las probes en verde y devuelve 401 en cada vista. Se crea tras el primer despliegue
y se guarda en el archivo cifrado:

```bash
kubectl exec deploy/all-in-django-api -- python manage.py createsuperuser
kubectl exec deploy/all-in-django-api -- python manage.py drf_create_token <usuario>
sops infra/helm/secretos/secretos.enc.yaml     # pegar el token ahí
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
| `postgres.enabled` | **`false`** | base **gestionada** (RDS) vía `secret.databaseUrl`. `true` levanta el StatefulSet embebido, útil en kind/minikube |
| `ingress.tls.enabled` | `false` | HTTPS con cert-manager: anotación + bloque `tls` |
| `ingress.tls.clusterIssuer` | `letsencrypt-staging` | **empezar por staging**: producción limita a 5 certificados por dominio y semana |
| `ingress.tls.email` | *(obligatorio si emite)* | cuenta ACME, para los avisos de caducidad |
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

## Secretos (SOPS + age)

Los valores sensibles —`secretKey`, `apiToken`, `databaseUrl`, `metricsToken`— viven en
**`infra/helm/secretos/secretos.enc.yaml`**, versionado y **cifrado**. No se pasan por `--set`:
un `--set` con un secreto queda en el historial del shell, en la salida de `ps` mientras el
comando corre, y en los logs de cualquier CI que lo ejecute.

**Por qué SOPS + age y no SealedSecrets**: SealedSecrets necesita un *controller corriendo en
el clúster*, y aquí el clúster todavía no existe. SOPS cifra en el repositorio, con una clave
local, y sirve igual para un `helm install` a mano hoy que para GitOps mañana. `age` en vez de
PGP: una clave de una línea, sin anillo de claves ni agente.

```bash
sops infra/helm/secretos/secretos.enc.yaml     # editar: descifra, abre el editor, recifra

# Desplegar sin dejar el plano en disco.
sops exec-file infra/helm/secretos/secretos.enc.yaml \
  'helm upgrade --install all-in-django infra/helm/all-in-django -f {}'
```

- La **clave privada** está en `%APPDATA%\sops\age\keys.txt` (Windows) o
  `~/.config/sops/age/keys.txt`. **No sale de la máquina, y sin ella el archivo cifrado es
  irrecuperable**: respáldala en un gestor de contraseñas. La pública sí se versiona, en
  `.sops.yaml` — para cifrar basta con esa.
- `encrypted_regex` cifra **solo los valores** sensibles: estructura y comentarios quedan
  legibles, así que un diff sigue siendo revisable.
- Lo versionado son **marcadores**, no credenciales. El de `secretKey` no pasa el gate de
  `core/conf.py` (≥ 50 caracteres, ≥ 5 distintos), así que un despliegue que olvide
  reemplazarlos **no arranca en silencio**: la API muere al iniciar diciendo por qué.
- `test_paridad_infra.py` falla si un valor sensible aparece en claro. Es lo único que impide
  commitear el archivo sin cifrar, porque nada obliga a editarlo con `sops`.

## HTTPS (Ingress + cert-manager)

```bash
sops exec-file infra/helm/secretos/secretos.enc.yaml \
  'helm upgrade --install all-in-django infra/helm/all-in-django -f {} \
     --set ingress.enabled=true --set ingress.host=app.tudominio.cl \
     --set ingress.className=nginx \
     --set ingress.tls.enabled=true --set ingress.tls.email=tu@correo.cl'
```

Con eso el Ingress gana la anotación `cert-manager.io/cluster-issuer` y un bloque `tls:`;
cert-manager crea el `Certificate` y **rellena solo** el Secret del certificado — por eso el
TLS queda fuera de SOPS: se emite y se renueva sin intervención.

**Empieza siempre por staging** (es el default). Producción limita a **5 certificados por
dominio y semana**: unos pocos intentos con el DNS mal apuntado agotan la cuota y dejan el
dominio sin poder emitir durante días. Staging no tiene ese límite y emite con una CA no
confiable — el navegador avisa, que es justo lo que quieres mientras compruebas el mecanismo.
Cuando emita bien, cambia el par:

```yaml
ingress:
  tls:
    clusterIssuer: letsencrypt-prod
    acmeServer: https://acme-v02.api.letsencrypt.org/directory
```

Requisitos que **no** están en el chart y sin los cuales el `Certificate` se queda en
`Pending` para siempre, sin error visible en el Ingress:

- **cert-manager instalado** en el clúster.
- Un **dominio real** apuntando al Ingress. `all-in-django.local` no sirve para emitir nada.
- El solver es **HTTP-01**: Let's Encrypt pide un fichero por HTTP en el propio dominio, así
  que el Ingress tiene que ser alcanzable **desde internet en el puerto 80**. En un clúster
  privado hay que usar DNS-01.

`crearClusterIssuer: false` si el clúster ya tiene el suyo: es un recurso *cluster-scoped* y
no debe haber dos con el mismo nombre.

## Base de datos: gestionada por defecto

`postgres.enabled` viene en **`false`**. El destino de este chart es AWS, donde el RDS ya lo
provisiona Terraform, y una base en un StatefulSet es de las cosas que peor envejecen en un
clúster: respaldos, failover y saltos de versión mayor pasan a ser tuyos.

El puente entre ambos mundos es el output de Terraform, que va al archivo cifrado y **no** a
un `--set`:

```bash
terraform -chdir=infra/terraform output -raw database_url
sops infra/helm/secretos/secretos.enc.yaml     # pegarlo en secret.databaseUrl
```

**Contrapartida asumida**: los valores de fábrica ya no despliegan solos — `helm install`
aborta pidiendo `secret.databaseUrl`. Es una excepción deliberada a la regla de que los
defaults funcionen (la que se aprendió con `image.tag: latest`), y se sostiene porque el
*tipo* de fallo es distinto: aquel daba un `ImagePullBackOff` mudo; este aborta en el render
diciendo exactamente qué falta. Para probar en local:

```bash
helm install ... --set postgres.enabled=true    # levanta el StatefulSet a propósito
```

## Producción
- ✅ Postgres gestionado ya es el **default** (`postgres.enabled=false`).
- ✅ HTTPS con Ingress + cert-manager disponible (`ingress.tls.enabled=true`). Fija además
  `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS` al dominio, y `SECURE_HTTPS=True` **solo** cuando
  el certificado ya emita: con TLS a medias, el redirect deja la app inalcanzable.
- ✅ `SECRET_KEY`/`DATABASE_URL`/`API_TOKEN`/`METRICS_TOKEN` ya salen de un archivo **cifrado
  con SOPS**, no de `--set` (ver *Secretos*).
- `test_paridad_infra.py` falla si una variable existe en el compose y no en el chart (o al
  revés): es lo único que impide que este chart vuelva a quedarse atrás.
