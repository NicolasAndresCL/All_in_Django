output "app_public_ip" {
  description = "IP pública de la EC2 (API en :8000, UI en :8501)."
  value       = aws_instance.app.public_ip
}

output "api_url" {
  value = "http://${aws_instance.app.public_ip}:8000"
}

output "ui_url" {
  value = "http://${aws_instance.app.public_ip}:8501"
}

output "db_endpoint" {
  description = "Endpoint del RDS Postgres."
  value       = aws_db_instance.postgres.address
}

output "database_url" {
  description = "DATABASE_URL completa (contiene la clave)."
  value       = local.database_url
  sensitive   = true
}
