# Maintenance Module

Terraform module for Azure Container Apps Job that runs automated database maintenance.

## Features

- Scheduled daily database cleanup (events, duplicates, orphans)
- Automatic VACUUM ANALYZE for performance
- Configurable retention and schedule
- VNet integration for security
- Application Insights logging

## Usage

```hcl
module "maintenance" {
  source = "./modules/maintenance"

  resource_group_name          = azurerm_resource_group.main.name
  location                     = azurerm_resource_group.main.location
  container_app_environment_id = azurerm_container_app_environment.main.id
  
  acr_login_server    = azurerm_container_registry.main.login_server
  acr_admin_username  = azurerm_container_registry.main.admin_username
  acr_admin_password  = azurerm_container_registry.main.admin_password
  
  db_host     = azurerm_postgresql_flexible_server.db.fqdn
  db_password = var.db_admin_password
}
```

## Deployment

Deploy and test the maintenance container:

```powershell
cd infrastructure/scripts
.\deploy-maintenance.ps1 -TestRun
```

## Documentation

See the wiki for complete documentation:

- [Maintenance Quick Reference](../wiki/MAINTENANCE_QUICK_REFERENCE.md)
- [Deployment Checklist](../wiki/MAINTENANCE_DEPLOYMENT_CHECKLIST.md)
- [Integration Guide](../wiki/MAINTENANCE_INTEGRATION.md)
- [Production Report](../wiki/MAINTENANCE_PRODUCTION_REPORT.md)

## Variables

See [variables.tf](variables.tf) for configuration options:

- `event_retention_days` - Days to retain events (default: 30)
- `schedule_cron` - Cron expression for schedule (default: daily 2 AM UTC)
- Container sizing and network options

## Outputs

- `job_id` - Container App Job resource ID
- `job_name` - Container App Job name
