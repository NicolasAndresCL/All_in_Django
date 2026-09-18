# Pruebas de la infraestructura con PROVEEDORES SIMULADOS (`mock_provider`): no hacen falta
# credenciales de AWS ni se crea nada de pago. Terraform evalua el grafo completo con
# valores inventados para lo que la nube calcularia (ids, IPs) y las aserciones miran lo
# que SI decide este codigo: reglas de red, respaldos, lo que el cloud-init inyecta y las
# validaciones de entrada.
#
# Que cazan y que no: cazan regresiones de configuracion (abrir el RDS, quitar el token de
# la UI, volver a `latest`). NO comprueban que AWS acepte el plan (cuotas, AMI existente,
# nombres de clase de instancia): eso solo lo dice un `plan` con credenciales.
#
#   terraform init -backend=false && terraform test

mock_provider "aws" {
  # Lo que la cuenta de AWS respondería; con el mock, una lista computada sale VACIA y
  # `subnet_ids[0]` reventaría antes de llegar a ninguna aserción.
  override_data {
    target = data.aws_subnets.default
    values = { ids = ["subnet-prueba-a", "subnet-prueba-b"] }
  }
  override_data {
    target = data.aws_vpc.default
    values = { id = "vpc-prueba" }
  }
  override_data {
    target = data.aws_ami.ubuntu
    values = { id = "ami-prueba-noble" }
  }
}

mock_provider "random" {}

# Valores validos por defecto; cada `run` sobreescribe lo que quiere romper.
variables {
  secret_key = "clave-de-prueba-larga-y-con-variedad-0123456789-abcdefghijklmnop"
  api_token  = "0123456789abcdef0123456789abcdef01234567"
  image_tag  = "v1.2.3"
}

# ─── Base de datos: privada, misma version que el resto del proyecto y con red de seguridad ──
run "rds_privado_y_con_respaldo" {
  command = plan

  assert {
    condition     = aws_db_instance.postgres.publicly_accessible == false
    error_message = "El RDS no puede ser publico: solo la EC2 de la app habla con el."
  }
  assert {
    condition     = aws_db_instance.postgres.engine == "postgres" && aws_db_instance.postgres.engine_version == "18"
    error_message = "Postgres 18 en los CUATRO sitios (compose x2, Helm, RDS): un dump -Fc sirve en cualquiera."
  }
  assert {
    condition     = aws_db_instance.postgres.skip_final_snapshot == false
    error_message = "Un destroy debe dejar snapshot final: sin el, los datos se van con la instancia."
  }
  assert {
    condition     = aws_db_instance.postgres.backup_retention_period > 0
    error_message = "Sin retencion de respaldos RDS no guarda nada y no hay point-in-time recovery."
  }
  assert {
    condition     = aws_db_instance.postgres.deletion_protection == true
    error_message = "deletion_protection debe venir activada por defecto."
  }
}

# ─── Red: Postgres SOLO desde el security group de la app ──────────────────────────────
run "postgres_solo_desde_la_app" {
  # `apply` simulado: los ids de los security groups son computados y en `plan` serian
  # desconocidos, y una asercion sobre un valor desconocido no puede evaluarse.
  assert {
    condition     = length(aws_security_group.db.ingress) == 1
    error_message = "El SG del RDS debe tener UNA sola regla de entrada (5432 desde la app)."
  }
  assert {
    condition     = one(aws_security_group.db.ingress).from_port == 5432 && one(aws_security_group.db.ingress).to_port == 5432
    error_message = "La unica entrada al RDS es el 5432."
  }
  assert {
    # Con el mock, un atributo no declarado llega como null (el proveedor real lo
    # normaliza a conjunto vacio): se aceptan las dos formas.
    condition     = one(aws_security_group.db.ingress).cidr_blocks == null || length(one(aws_security_group.db.ingress).cidr_blocks) == 0
    error_message = "El RDS no admite CIDRs: la entrada se restringe por security group, no por IP."
  }
  assert {
    condition     = contains(one(aws_security_group.db.ingress).security_groups, aws_security_group.app.id)
    error_message = "La entrada al RDS debe venir del SG de la app."
  }
  assert {
    condition     = contains(aws_instance.app.vpc_security_group_ids, aws_security_group.app.id)
    error_message = "La EC2 debe llevar el SG de la app (o el RDS no la dejara entrar)."
  }
}

# ─── SSH: el CIDR de la variable es el que llega a la regla ────────────────────────────
run "ssh_restringido_al_cidr_indicado" {
  command = plan
  variables {
    ssh_ingress_cidr = "203.0.113.7/32"
  }

  assert {
    condition     = length(one([for r in aws_security_group.app.ingress : r if r.from_port == 22]).cidr_blocks) == 1 && contains(one([for r in aws_security_group.app.ingress : r if r.from_port == 22]).cidr_blocks, "203.0.113.7/32")
    error_message = "La regla SSH debe usar exactamente ssh_ingress_cidr."
  }
  assert {
    condition     = length([for r in aws_security_group.app.ingress : r if r.from_port == 22]) == 1
    error_message = "Solo una regla SSH en el SG de la app."
  }
}

# ─── cloud-init: lo que la EC2 va a ejecutar de verdad ─────────────────────────────────
run "cloud_init_inyecta_lo_que_el_stack_necesita" {
  # `apply` simulado: DATABASE_URL lleva el endpoint del RDS y la clave de random_password,
  # ambos computados.

  assert {
    # Con core.autocrlf=true en Windows la plantilla llega con CRLF si .gitattributes no
    # la fuerza a LF, y cloud-init muere en `#!/bin/bash\r` sin dejar la app levantada.
    condition     = !can(regex("\r", aws_instance.app.user_data))
    error_message = "El cloud-init lleva retornos de carro (CRLF): la EC2 no lo ejecutara. Revisa .gitattributes (*.tftpl eol=lf)."
  }
  assert {
    condition     = can(regex("SECRET_KEY=clave-de-prueba", aws_instance.app.user_data))
    error_message = "cloud-init debe escribir SECRET_KEY en .env.docker."
  }
  assert {
    condition     = can(regex("DEBUG=False", aws_instance.app.user_data))
    error_message = "La EC2 corre con DEBUG=False."
  }
  assert {
    condition     = can(regex("DATABASE_URL=postgres://app:[^@\n]+@[^:\n]+:5432/all_in_django", aws_instance.app.user_data))
    error_message = "DATABASE_URL debe apuntar al RDS con usuario, clave, host y base."
  }
  assert {
    condition     = can(regex("API_TOKEN=0123456789abcdef0123456789abcdef01234567", aws_instance.app.user_data))
    error_message = "La UI necesita API_TOKEN o levanta 'healthy' dando 401 en cada vista (fallo del 2026-08-18)."
  }
  assert {
    condition     = can(regex("rest_framework.authtoken.models import Token", aws_instance.app.user_data)) && can(regex("key='0123456789abcdef0123456789abcdef01234567'", aws_instance.app.user_data))
    error_message = "cloud-init debe dar de alta en la base el MISMO token que recibe la UI."
  }
  assert {
    condition     = can(regex("docker compose up -d --wait", aws_instance.app.user_data))
    error_message = "El alta del token corre tras `up -d --wait`: antes, la base puede estar a medio migrar."
  }
  assert {
    condition     = length(regexall("ghcr.io/nicolasandrescl/all-in-django-(api|ui):v1.2.3", aws_instance.app.user_data)) == 2
    error_message = "Las dos imagenes (api y ui) deben llevar el image_tag indicado."
  }
  assert {
    condition     = !can(regex(":latest", aws_instance.app.user_data))
    error_message = "Ninguna imagen puede ir en :latest (GHCR no lo publica)."
  }
  assert {
    condition     = can(regex("http://", output.api_url)) && can(regex(":8501", output.ui_url))
    error_message = "Los outputs api_url/ui_url deben apuntar a los puertos publicados."
  }
}

# ─── Validaciones de entrada: los valores que NO deben pasar del `plan` ────────────────
run "rechaza_image_tag_latest" {
  command = plan
  variables {
    image_tag = "latest"
  }
  expect_failures = [var.image_tag]
}

run "rechaza_image_tag_vacio" {
  command = plan
  variables {
    image_tag = ""
  }
  expect_failures = [var.image_tag]
}

run "rechaza_secret_key_debil" {
  command = plan
  variables {
    secret_key = "corta"
  }
  expect_failures = [var.secret_key]
}

run "rechaza_secret_key_sin_variedad" {
  command = plan
  variables {
    # 60 caracteres, pero solo 2 distintos: core/conf.py la rechazaria en el arranque.
    secret_key = "ababababababababababababababababababababababababababababababab"
  }
  expect_failures = [var.secret_key]
}

run "rechaza_api_token_corto_o_no_hex" {
  command = plan
  variables {
    api_token = "no-es-un-token-drf"
  }
  expect_failures = [var.api_token]
}
