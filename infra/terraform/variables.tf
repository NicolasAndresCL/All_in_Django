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
  description = "Tag de las imágenes a desplegar."
  type        = string
  default     = "latest"
}
