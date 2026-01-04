# ReportMate Infrastructure Outputs

# Functions Outputs
output "function_app_name" {
  description = "Name of the Azure Functions App"
  value       = module.functions.function_app_name
}

output "function_app_url" {
  description = "Default hostname of the Functions App"
  value       = module.functions.function_app_default_hostname
}

output "function_app_identity_principal_id" {
  description = "Principal ID of the Functions App managed identity"
  value       = module.functions.function_app_identity_principal_id
}

# Maintenance Job Outputs
output "maintenance_job_name" {
  description = "Name of the database maintenance job"
  value       = module.maintenance.job_name
}

output "maintenance_schedule" {
  description = "Cron schedule for maintenance job"
  value       = module.maintenance.schedule
}

output "maintenance_job_id" {
  description = "ID of the Container App Job for maintenance"
  value       = module.maintenance.job_id
}
