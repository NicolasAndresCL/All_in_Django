terraform {
  # >= 1.10 por `use_lockfile` del backend s3 (bloqueo nativo, sin DynamoDB).
  required_version = ">= 1.10"

  # Estado REMOTO. Con el estado en el disco de una sola maquina, `apply` es de un solo
  # operador y un .tfstate perdido deja recursos de pago huerfanos que nadie sabe que
  # existen. Ademas el estado contiene secretos (la clave del RDS), asi que va cifrado.
  #
  # El bloqueo usa `use_lockfile` (un objeto .tflock junto al estado) y NO DynamoDB: la
  # documentacion de HashiCorp marca el bloqueo por DynamoDB como deprecado y a retirar
  # en una version futura. Un recurso de pago menos y la via soportada a futuro.
  #
  # Configuracion PARCIAL a proposito: `bucket` y `region` dependen de la cuenta (el
  # nombre de un bucket S3 es unico en todo AWS) y se pasan al init. Ver backend.hcl.example.
  #
  #   terraform init -backend-config=backend.hcl
  #
  # Sin el bucket creado todavia, para validar en local:  terraform init -backend=false
  backend "s3" {
    key          = "all-in-django/terraform.tfstate"
    encrypt      = true
    use_lockfile = true
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

provider "aws" {
  region = var.aws_region
}
