output "job_id" {
  description = "ID of the Container App Job"
  value       = azurerm_container_app_job.maintenance.id
}

output "job_name" {
  description = "Name of the Container App Job"
  value       = azurerm_container_app_job.maintenance.name
}

output "schedule" {
  description = "Cron schedule for maintenance job"
  value       = var.schedule_cron
}
