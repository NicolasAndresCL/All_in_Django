# Terraform — All in Django (AWS)

Provisiona la infra mínima para correr la app en AWS:

- **RDS Postgres 16** (base gestionada, privada).
- **EC2 Ubuntu 24.04** que instala Docker y corre `docker compose up` con las imágenes de
  GHCR (`all-in-django-api` / `-ui`) apuntando al RDS. Ver `templates/cloud-init.sh.tftpl`.
- **Security groups**: EC2 pública en 8000/8501/22; RDS accesible solo desde la EC2.

> Es un **skeleton** con `default` VPC/subnets. El proveedor por defecto es AWS; es
> intercambiable por DigitalOcean/GCP cambiando `versions.tf` y ~2 recursos.

## Requisitos
- Terraform >= 1.6, credenciales AWS (`aws configure` o variables de entorno).
- Las imágenes publicadas en GHCR (workflow `docker-publish.yml`, al crear un tag `vX.Y.Z`).

## Uso
```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars   # completa secret_key, images_owner, etc.

terraform init
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

## Notas de seguridad
- `secret_key` y la clave del RDS (`random_password`) son `sensitive`; no se imprimen.
- Restringe `ssh_ingress_cidr` a tu IP. Para producción real, pon la app tras HTTPS
  (ALB/Nginx + certificado) y no expongas 8000/8501 directo.
- El estado (`*.tfstate`) contiene secretos: está gitignored; usa un backend remoto
  (S3 + DynamoDB lock) para trabajo en equipo.
