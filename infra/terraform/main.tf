# Infra mínima en AWS para All in Django:
#   - RDS Postgres (base gestionada)
#   - EC2 que corre `docker compose up` con las imágenes de GHCR, apuntando al RDS
#   - Security groups (EC2 público en 8000/8501/22; RDS solo accesible desde la EC2)
#
# Es un SKELETON: revisa costos antes de `terraform apply` (RDS + EC2 son de pago).
# Swappable a DigitalOcean/GCP cambiando el provider y ~2 recursos.

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }
}

resource "random_password" "db" {
  length  = 24
  special = false
}

# ─── Security groups ─────────────────────────────────────────────────────────
resource "aws_security_group" "app" {
  name_prefix = "${var.project}-app-"
  description = "All in Django EC2 (API 8000, UI 8501, SSH)"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "API"
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    description = "UI NiceGUI"
    from_port   = 8501
    to_port     = 8501
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.ssh_ingress_cidr]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "db" {
  name_prefix = "${var.project}-db-"
  description = "Postgres accesible solo desde la EC2 de la app"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description     = "Postgres desde la app"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# ─── Base de datos gestionada (RDS Postgres) ─────────────────────────────────
resource "aws_db_subnet_group" "this" {
  name_prefix = "${var.project}-"
  subnet_ids  = data.aws_subnets.default.ids
}

resource "aws_db_instance" "postgres" {
  identifier_prefix      = "${var.project}-"
  engine                 = "postgres"
  engine_version         = "16"
  instance_class         = var.db_instance_class
  allocated_storage      = 20
  db_name                = var.db_name
  username               = var.db_username
  password               = random_password.db.result
  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [aws_security_group.db.id]
  skip_final_snapshot    = true
  publicly_accessible    = false
}

locals {
  database_url = "postgres://${var.db_username}:${random_password.db.result}@${aws_db_instance.postgres.address}:5432/${var.db_name}"
}

# ─── EC2 que corre docker compose ────────────────────────────────────────────
resource "aws_instance" "app" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  subnet_id              = data.aws_subnets.default.ids[0]
  vpc_security_group_ids = [aws_security_group.app.id]
  key_name               = var.ssh_key_name != "" ? var.ssh_key_name : null

  user_data = templatefile("${path.module}/templates/cloud-init.sh.tftpl", {
    database_url  = local.database_url
    secret_key    = var.secret_key
    allowed_hosts = var.allowed_hosts
    images_owner  = var.images_owner
    image_tag     = var.image_tag
  })

  tags = { Name = "${var.project}-app" }

  depends_on = [aws_db_instance.postgres]
}
