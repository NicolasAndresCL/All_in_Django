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
  (`aws configure` o variables de entorno). En esta máquina no está instalado: sirve igual
  `docker run --rm -v <ruta>:/tf -w /tf hashicorp/terraform:1.16.3` (la versión fija del CI).
- Un **bucket S3 para el estado** ya creado (ver más abajo).
- Las imágenes publicadas en GHCR (workflow `docker-publish.yml`, al crear un tag `vX.Y.Z`).
  **`image_tag` no tiene default y rechaza `latest`**: GHCR nunca lo tiene, y con él el
  `docker compose pull` del cloud-init moría en la primera EC2 sin más rastro que su log.
- Un **`api_token`** (40 hex: `python -c "import secrets; print(secrets.token_hex(20))"`).
  El cloud-init lo da de alta en la base (usuario de servicio `ui`, sin contraseña) y se lo
  pasa a la UI. Sin él el stack levantaba `healthy` con la UI dando 401 en cada vista — el
  mismo falso positivo que Compose corta con `${API_TOKEN:?}` y Helm con `required`.

## Uso
```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars   # completa secret_key, images_owner, etc.

terraform init -backend-config=backend.hcl   # estado remoto (ver "Estado remoto")
terraform validate
terraform test        # gratis: proveedores simulados (ver "Pruebas sin credenciales")
terraform plan        # gratis: no crea nada, pero sí exige credenciales AWS
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
terraform fmt -check -diff -recursive
terraform init -backend=false
terraform validate
terraform test
```

`.terraform.lock.hcl` **se versiona** (es el `package-lock` de los proveedores: mismo `aws`
5.x en tu máquina y en el CI) y lleva hashes de `linux_amd64` **y** `windows_amd64` — solo
con los de Windows, el `init` de Ubuntu fallaría por checksum. Tras cambiar una versión:
`terraform providers lock -platform=linux_amd64 -platform=windows_amd64`.

## Pruebas sin credenciales (`terraform test`)

`tests/infra.tftest.hcl` ejecuta el grafo completo con **proveedores simulados**
(`mock_provider "aws"` / `"random"`): AWS no recibe ni una llamada, no hace falta cuenta y no
se crea nada de pago. Lo que la nube calcularía (ids, IPs, la clave de `random_password`) sale
inventado; las aserciones miran lo que **este código** decide:

| `run` | Qué afirma |
|---|---|
| `rds_privado_y_con_respaldo` | `publicly_accessible=false`, Postgres **18**, snapshot final, retención > 0, `deletion_protection` |
| `postgres_solo_desde_la_app` | el SG del RDS tiene **una** regla: 5432 desde el SG de la app, sin CIDRs; la EC2 lleva ese SG |
| `ssh_restringido_al_cidr_indicado` | la regla 22 usa exactamente `ssh_ingress_cidr` |
| `cloud_init_inyecta_lo_que_el_stack_necesita` | el `user_data` lleva `SECRET_KEY`, `DEBUG=False`, `DATABASE_URL` al RDS, **`API_TOKEN`** (y su alta en la base con la **misma** clave), `up -d --wait` antes del alta, las dos imágenes con el `image_tag` pedido, nada en `:latest` y **ningún CRLF** |
| `rechaza_*` (5) | las `validation` de `image_tag` (vacío/`latest`), `secret_key` (< 50 chars o < 5 distintos, el gate de `core/conf.py`) y `api_token` (no hex o corto) abortan en el `plan` |

Se ha comprobado que **falla cuando debe**: con `publicly_accessible = true` o sin la línea
`API_TOKEN=` del cloud-init, la prueba se pone en rojo con el mensaje que explica el porqué.
Corre en el job `terraform` del CI (después de `lint`, en paralelo con los tests) y en
`scripts/verificar.ps1`.

**Lo que NO cubre**: que AWS acepte el plan (cuotas, clase de instancia disponible en la
región, AMI existente). Eso solo lo dice `terraform plan` con credenciales.

Tres cosas del simulador que cuestan un rato:

- Una lista **computada** sale **vacía** con el mock (`data.aws_subnets.default.ids`), y
  `subnet_ids[0]` revienta antes de llegar a ninguna aserción: se rellena con
  `override_data` dentro del `mock_provider`.
- Un atributo que la configuración **no declara** llega como `null`, no como conjunto vacío
  como lo normalizaría el proveedor real (`cidr_blocks` de la regla del RDS): la aserción
  acepta las dos formas.
- Los `run` que miran ids o `DATABASE_URL` van en modo `apply` (simulado): en `plan` esos
  valores son *desconocidos* y una condición sobre un desconocido no se puede evaluar. Al
  revés, `expect_failures` sobre una `validation` **solo** funciona con `command = plan`.

**CRLF**: `templatefile()` lee la plantilla del **disco**, y con `core.autocrlf=true` un
checkout de Windows la deja con `
` — la EC2 recibiría `#!/bin/bash` y cloud-init no la
ejecutaría, sin error en Terraform. `.gitattributes` fuerza `eol=lf` en `templates/*.tftpl`
y la prueba lo vigila.

## Notas de seguridad
- `secret_key`, `api_token` y la clave del RDS (`random_password`) son `sensitive`; no se
  imprimen. En la EC2, la UI recibe solo `.env.ui` (`API_BASE` + `API_TOKEN`), no el
  `.env.docker` entero con `SECRET_KEY` y `DATABASE_URL`; ambos archivos van con `chmod 600`.
- Restringe `ssh_ingress_cidr` a tu IP. Para producción real, pon la app tras HTTPS
  (ALB/Nginx + certificado) y no expongas 8000/8501 directo.
- El estado contiene secretos: además de estar gitignored, va **cifrado en S3** (ver *Estado
  remoto*). `backend.hcl` también está gitignored: lleva el nombre del bucket, que es
  información de la cuenta.
