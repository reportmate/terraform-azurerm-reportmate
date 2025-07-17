# ReportMate Azure Infrastructure Module

This Terraform module deploys a complete ReportMate infrastructure on Azure, including PostgreSQL database, Azure Functions for the API, storage, monitoring, and networking components.

## Features

- **PostgreSQL Flexible Server** - Managed database with high availability
- **Azure Functions** - Serverless API endpoints for device management and data ingestion
- **Application Insights** - Comprehensive monitoring and logging
- **Storage Account** - Blob storage for device data and artifacts
- **Front Door CDN** - Global load balancing and custom domain support

## Usage

```hcl
module "reportmate" {
  source = "your-org/reportmate/azurerm"
  
  resource_group_name      = "reportmate-prod"
  location                = "East US"
  database_admin_username  = "reportmate_admin"
  database_admin_password  = var.database_password
  
  custom_domain = "api.yourcompany.com"  # optional
  
  tags = {
    Environment = "production"
    Project     = "ReportMate"
    Owner       = "IT Team"
  }
}
```

## Requirements

| Name | Version |
|------|---------|
| terraform | >= 1.0 |
| azurerm | ~> 3.0 |
| random | ~> 3.1 |

## Providers

| Name | Version |
|------|---------|
| azurerm | ~> 3.0 |
| random | ~> 3.1 |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| resource_group_name | Name of the Azure Resource Group | `string` | n/a | yes |
| database_admin_username | Administrator username for PostgreSQL server | `string` | n/a | yes |
| database_admin_password | Administrator password for PostgreSQL server | `string` | n/a | yes |
| location | Azure region where resources will be deployed | `string` | `"East US"` | no |
| database_name | Name of the PostgreSQL database | `string` | `"reportmate"` | no |
| custom_domain | Custom domain for the ReportMate API | `string` | `null` | no |
| tags | Tags to apply to all resources | `map(string)` | `{"Environment": "production", "Project": "ReportMate"}` | no |

## Outputs

| Name | Description |
|------|-------------|
| resource_group_name | Name of the created resource group |
| database_server_fqdn | Fully qualified domain name of the PostgreSQL server |
| database_connection_string | Connection string for the PostgreSQL database |
| function_app_url | URL of the Function App |
| function_app_hostname | Hostname of the Function App |
| storage_account_name | Name of the storage account |
| application_insights_instrumentation_key | Application Insights instrumentation key |
| front_door_endpoint | Front Door endpoint URL |

## Architecture

The module creates the following Azure resources:

1. **Resource Group** - Container for all resources
2. **PostgreSQL Flexible Server** - Primary database
3. **Storage Account** - Blob storage with containers
4. **Application Insights** - Monitoring and telemetry
5. **Function App** - API endpoints and data processing
6. **Front Door** - CDN and custom domain support

## API Endpoints

Once deployed, the following endpoints are available:

- `POST /api/ingest` - Device data ingestion
- `GET /api/devices` - List all devices
- `GET /api/devices/{id}` - Get specific device
- `GET /api/health` - Health check

## Security

- Database uses Azure Active Directory authentication
- Function App uses managed identity
- Storage account uses private endpoints where possible
- All traffic encrypted in transit

## Support

For issues and questions, please refer to the ReportMate documentation or open an issue in the repository.
