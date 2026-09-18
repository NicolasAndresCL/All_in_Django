variable "aws_region" {
  description = "Región de AWS."
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Prefijo para nombrar los recursos."
  type        = string
  default     = "all-in-django"
}

variable "instance_type" {
  description = "Tipo de EC2 que corre docker compose."
  type        = string
  default     = "t3.small"
}

variable "db_instance_class" {
  description = "Clase de la instancia RDS Postgres."
  type        = string
  default     = "db.t3.micro"
}

variable "db_name" {
  description = "Nombre de la base de datos."
  type        = string
  default     = "all_in_django"
}

variable "db_username" {
  description = "Usuario maestro de Postgres."
  type        = string
  default     = "app"
}

variable "ssh_key_name" {
  description = "Nombre de un key pair EC2 existente para acceso SSH (opcional)."
  type        = string
  default     = ""
}

variable "ssh_ingress_cidr" {
  description = "CIDR permitido para SSH (restríngelo a tu IP)."
  type        = string
  default     = "0.0.0.0/0"
}

variable "secret_key" {
  description = "SECRET_KEY de Django (inyectada al contenedor). NO la pongas en el repo."
  type        = string
  sensitive   = true

  # Mismo gate que core/conf.py (>= 50 caracteres y >= 5 distintos). Si no se valida aqui,
  # el contenedor muere en el arranque de la EC2 con el error dentro del cloud-init, donde
  # nadie lo mira; aqui aborta en el `plan`, con el nombre de la variable.
  validation {
    condition     = length(var.secret_key) >= 50 && length(distinct(split("", var.secret_key))) >= 5
    error_message = "secret_key debil: se exigen >= 50 caracteres y >= 5 distintos (igual que core/conf.py)."
  }
}

variable "api_token" {
  description = "Token DRF con el que la UI llama a la API (cloud-init lo crea en la base). NO lo pongas en el repo."
  type        = string
  sensitive   = true

  # Sin el, el stack levanta 'healthy' con la UI dando 401 en cada vista: el falso positivo
  # del 2026-08-18 que Compose ya corta con `${API_TOKEN:?}` y Helm con `required`.
  validation {
    condition     = length(var.api_token) >= 40 && can(regex("^[0-9a-f]+$", var.api_token))
    error_message = "api_token debe ser hexadecimal de >= 40 caracteres (formato de token DRF): python -c \"import secrets; print(secrets.token_hex(20))\"."
  }
}

variable "allowed_hosts" {
  description = "ALLOWED_HOSTS de Django (CSV). Incluye el dominio/IP pública."
  type        = string
  default     = "*"
}

variable "images_owner" {
  description = "Owner en GHCR de las imágenes (ghcr.io/<owner>/all-in-django-{api,ui})."
  type        = string
  default     = "nicolasandrescl"
}

variable "image_tag" {
  description = "Tag de las imagenes a desplegar (vX.Y.Z). Sin default: en produccion se elige a proposito."
  type        = string

  # `latest` NO existe en GHCR (docker-publish.yml solo publica semver+sha): con ese valor
  # el `docker compose pull` del cloud-init falla en la primera EC2, sin mas rastro que el
  # log de cloud-init. Misma regla que el Jenkinsfile (aborta con vacio o `latest`) y que
  # el chart de Helm (resuelve al appVersion).
  validation {
    condition     = var.image_tag != "" && var.image_tag != "latest"
    error_message = "image_tag no puede ser vacio ni 'latest' (GHCR no lo publica); usa un tag vX.Y.Z existente."
  }
}

variable "db_backup_retention_days" {
  description = "Dias de retencion de los respaldos automaticos de RDS (0 los desactiva)."
  type        = number
  default     = 7
}

variable "db_deletion_protection" {
  description = "Impide destruir la instancia RDS desde la API/consola sin desactivarlo antes."
  type        = bool
  default     = true
}
