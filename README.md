# ReportMate Azure Infrastructure Module

This Terraform module deploys a complete ReportMate infrastructure on Azure, including PostgreSQL database, Azure Functions for the API, storage, monitoring, and networking components.

## Features

- **PostgreSQL Flexible Server** - Managed database with high availability
- **Azure Functions** - Serverless API endpoints for device management and data ingestion
- **Application Insights** - Comprehensive monitoring and logging
- **Storage Account** - Blob storage for device data and artifacts
- **Front Door CDN** - Global load balancing and custom domain support

## Usage

\\\hcl
module \
reportmate\ {
  source = \reportmate/reportmate/azurerm\
  
  resource_group_name      = \reportmate-prod\
  location                = \East
US\
  database_admin_username  = \reportmate_admin\
  database_admin_password  = var.database_password
  custom_domain = \api.yourcompany.com\  # optional
  tags = {
    Environment = \production\
    Project     = \ReportMate\
    Owner       = \IT
Team\
  }
}
\\\

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

- \POST /api/ingest\ - Device data ingestion
- \GET /api/devices\ - List all devices
- \GET /api/devices/{id}\ - Get specific device
- \GET /api/health\ - Health check

## Support

For issues and questions, please refer to the ReportMate documentation or open an issue in the repository.
