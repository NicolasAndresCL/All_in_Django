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
| `image.tag` | `latest` | tag a desplegar |
| `secret.secretKey` | *(obligatorio)* | SECRET_KEY de Django |
| `postgres.enabled` | `true` | `false` → usa base gestionada vía `secret.databaseUrl` |
| `config.ALLOWED_HOSTS` | `*` | ajusta al dominio del Ingress |
| `ingress.enabled` | `false` | activa el Ingress (UI en `/`, API en `/api`,`/admin`,`/static`) |

## Producción
- Prefiere Postgres gestionado (`postgres.enabled=false` + `secret.databaseUrl`) sobre el
  StatefulSet embebido.
- Sirve tras HTTPS (Ingress + cert-manager) y fija `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS`.
- Gestiona `SECRET_KEY`/`DATABASE_URL` con un Secret externo (SealedSecrets/SOPS), no `--set`.
