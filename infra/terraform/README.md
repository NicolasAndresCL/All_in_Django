# Terraform — All in Django (AWS)

Provisiona la infra mínima para correr la app en AWS:

- **RDS Postgres 18** (base gestionada, privada). Mismo mayor que Compose y Helm: un
  dump `-Fc` sirve en cualquier entorno.
- **EC2 Ubuntu 24.04** que instala Docker y corre `docker compose up` con las imágenes de
  GHCR (`all-in-django-api` / `-ui`) apuntando al RDS. Ver `templates/cloud-init.sh.tftpl`.
- **Security groups**: EC2 pública en 8000/8501/22; RDS accesible solo desde la EC2.

> Es un **skeleton** con `default` VPC/subnets. El proveedor por defecto es AWS; es
> intercambiable por DigitalOcean/GCP cambiando `versions.tf` y ~2 recursos.

## Requisitos
- Terraform >= 1.10 (por `use_lockfile` del backend), credenciales AWS
  (`aws configure` o variables de entorno).
- Un **bucket S3 para el estado** ya creado (ver más abajo).
- Las imágenes publicadas en GHCR (workflow `docker-publish.yml`, al crear un tag `vX.Y.Z`).

## Uso
```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars   # completa secret_key, images_owner, etc.

terraform init -backend-config=backend.hcl   # estado remoto (ver "Estado remoto")
terraform validate
terraform plan        # gratis: no crea nada
terraform apply       # ⚠️ crea RDS + EC2 (recursos de PAGO)

terraform output ui_url
```

Semilla de datos (una vez, por SSH a la EC2):
```bash
docker compose run --rm api python manage.py loaddata fixtures/datos_sqlite.json
# (requiere subir fixtures/datos_sqlite.json a la instancia)
```

Destruir todo:
```bash
terraform destroy
```

## Estado remoto (backend S3)

El estado vive en **S3, cifrado y versionado**, no en el disco. Con el estado local, `apply`
es de un solo operador y una sola máquina, y un `terraform.tfstate` perdido deja recursos de
pago **huérfanos que nadie sabe que existen**. Además el estado contiene secretos (la clave
del RDS), así que va cifrado.

El bloqueo usa **`use_lockfile`** (un objeto `.tflock` junto al estado) y **no DynamoDB**: la
documentación de HashiCorp marca el bloqueo por DynamoDB como *deprecado y a retirar en una
versión futura*. Un recurso de pago menos y la vía soportada a futuro — a cambio de exigir
Terraform >= 1.10.

`bucket` y `region` no van en el código (el nombre de un bucket S3 es único en **todo** AWS y
depende de la cuenta): se pasan como **configuración parcial**.

```bash
cp backend.hcl.example backend.hcl    # gitignored; pon ahí tu bucket
terraform init -backend-config=backend.hcl
```

**El bucket no lo crea este proyecto**: es el huevo y la gallina —no puede guardar su propio
estado dentro de sí mismo— y es un recurso de pago. Se crea una vez; los comandos exactos
(versionado, cifrado y bloqueo de acceso público) están en `backend.hcl.example`. El
**versionado no es opcional**: es lo único que permite recuperar un estado corrupto o borrado
por error.

Para validar el HCL sin bucket ni credenciales:

```bash
terraform fmt -check -diff
terraform init -backend=false
terraform validate
```

## Notas de seguridad
- `secret_key` y la clave del RDS (`random_password`) son `sensitive`; no se imprimen.
- Restringe `ssh_ingress_cidr` a tu IP. Para producción real, pon la app tras HTTPS
  (ALB/Nginx + certificado) y no expongas 8000/8501 directo.
- El estado contiene secretos: además de estar gitignored, va **cifrado en S3** (ver *Estado
  remoto*). `backend.hcl` también está gitignored: lleva el nombre del bucket, que es
  información de la cuenta.
