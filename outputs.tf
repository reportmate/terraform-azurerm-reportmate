# ReportMate Infrastructure Outputs

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
