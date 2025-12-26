# ReportMate Azure Terraform Module

![ReportMate](https://img.shields.io/badge/ReportMate-v1.0-blue)
![Terraform](https://img.shields.io/badge/Terraform-%3E%3D1.12-purple)
![Azure](https://img.shields.io/badge/Azure-Cloud-blue)

A comprehensive Terraform module for deploying ReportMate infrastructure on Azure. This module provisions a complete osquery fleet management platform with web interface, API, real-time messaging, and monitoring.

## 📁 Directory Structure

```
infrastructure/
├── main.tf             # Primary infrastructure definition
├── variables.tf        # Input variables
├── outputs.tf          # Output values
├── versions.tf         # Provider and version constraints
├── backend.tf          # State backend configuration
├── modules/            # Reusable Terraform modules
│   ├── database/       # PostgreSQL database module
│   ├── storage/        # Azure Storage module
│   ├── messaging/      # Web PubSub module
│   ├── monitoring/     # Application Insights module
│   ├── identity/       # Managed Identity module
│   ├── containers/     # Container Apps module
│   └── networking/     # Front Door module
├── api/                # FastAPI container application
├── scripts/            # Deployment and utility scripts
├── schemas/            # Database schemas and migrations
├── wiki/               # Detailed documentation and guides
└── examples/           # Example configurations
```

For detailed documentation, see [wiki/README.md](./wiki/README.md)

## 🚀 Quick Start

### Prerequisites

**Required Tools:**
- **Azure CLI**: `winget install Microsoft.AzureCLI` or [Download](https://learn.microsoft.com/cli/azure/install-azure-cli)
- **Terraform**: `winget install Hashicorp.Terraform` or [Download](https://www.terraform.io/downloads)
- **PowerShell 7+**: `winget install Microsoft.PowerShell` (for scripts)

**Azure Authentication:**
```powershell
az login
az account set --subscription "<your-subscription-id>"
az account show  # Verify your account
```

### Bootstrap Deployment (Recommended)

For a fresh deployment, use the canonical bootstrap script:

```powershell
# Complete bootstrap (infrastructure + database + functions)
.\scripts\bootstrap.ps1

# With auto-approval for CI/CD pipelines
.\scripts\bootstrap.ps1 -AutoApprove -Validate
```

The bootstrap script handles:
- Terraform backend configuration validation
- Infrastructure provisioning
- Database schema initialization
- Container deployments

### Individual Component Deployment

**Deploy FastAPI Container (API code changes):**
```powershell
.\scripts\deploy-api.ps1 -ForceBuild
```

**Deploy Frontend Container (web app changes):**
```powershell
.\scripts\deploy-containers.ps1 -Environment prod -ForceBuild
```

**Deploy Database Maintenance Jobs:**
```powershell
.\scripts\deploy-maintenance.ps1
```

**Check System Status:**
```powershell
.\scripts\check.ps1              # Basic health check
.\scripts\check.ps1 -FixIssues   # Attempt to fix issues
.\scripts\status.ps1             # Detailed component status
```

### Manual Terraform Deployment

If you prefer manual control or CI/CD integration:

**1. Configure Terraform Backend:**
```powershell
# One-time setup: Create storage account for Terraform state
az group create --name Terraform --location canadacentral
az storage account create --name youruniquename --resource-group Terraform --sku Standard_LRS
az storage container create --name terraform-state --account-name youruniquename

# Create backend configuration from example
Copy-Item backend.tf.example backend.tf
# Edit backend.tf with your storage account details
# NOTE: backend.tf is gitignored - never commit it!
```

**2. Configure Variables:**
```powershell
# Copy and configure variables
Copy-Item terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your deployment values
# NOTE: terraform.tfvars is gitignored - contains secrets!
```

**3. Deploy Infrastructure:**
```powershell
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

**4. Initialize Database:**
```powershell
# Via API endpoint (recommended)
curl "https://reportmate-functions-api.<your-subdomain>.azurecontainerapps.io/api/init-db?init=true"

# Or manually via psql
psql "postgresql://reportmate:PASSWORD@reportmate-database.postgres.database.azure.com:5432/reportmate?sslmode=require" -f schemas/database.sql
```

## 🛠️ Deployment Scripts

ReportMate includes comprehensive deployment scripts in `./scripts/`:

| Script | Purpose | Usage |
|--------|---------|-------|
| `bootstrap.ps1` | Complete initial deployment | `.\scripts\bootstrap.ps1` |
| `deploy-api.ps1` | Deploy FastAPI container | `.\scripts\deploy-api.ps1 -ForceBuild` |
| `deploy-containers.ps1` | Deploy frontend container | `.\scripts\deploy-containers.ps1 -Environment prod -ForceBuild` |
| `deploy-maintenance.ps1` | Deploy maintenance jobs | `.\scripts\deploy-maintenance.ps1` |
| `check.ps1` | Health checks and diagnostics | `.\scripts\check.ps1` |
| `status.ps1` | Detailed component status | `.\scripts\status.ps1` |

**Key Features:**
- Cross-platform PowerShell scripts (Windows, macOS, Linux)
- Auto-detects environment and provides intelligent deployment options
- Comprehensive error handling and validation
- Supports `-ForceBuild` for clean rebuilds without Docker cache
- Automated health checks and verification

## Architecture

ReportMate provides a complete osquery fleet management platform with:

- **💻 Web Application**: Next.js frontend with real-time dashboard and modular architecture
- **🚀 Powerful REST API**: Complete Azure Functions-based API with 9 specialized data processors
- **🗄️ Database**: PostgreSQL for storing osquery results and configurations with business unit support
- **⚡ Real-time Messaging**: Azure Web PubSub for live fleet updates and notifications
- **📦 Container Platform**: Azure Container Apps for scalable web hosting
- **📊 Monitoring**: Application Insights for comprehensive observability and analytics
- **🔒 Security**: Machine group authentication, business unit access control, and managed identities

### REST API Endpoints

The ReportMate API provides comprehensive endpoints for fleet management:

#### Core Device Endpoints
- **POST** `/api/v1/devices/ingest` - Enhanced device data ingestion with 9-module processing
- **GET** `/api/v1/devices` - List all devices with filtering and pagination  
- **GET** `/api/v1/devices/{id}` - Get detailed device information with all modules
- **DELETE** `/api/v1/devices/{id}` - Remove device from fleet

#### Device-Specific Module Endpoints
- **GET** `/api/v1/devices/{id}/applications` - Device applications inventory
- **GET** `/api/v1/devices/{id}/hardware` - Device hardware specifications
- **GET** `/api/v1/devices/{id}/security` - Device security posture and compliance
- **GET** `/api/v1/devices/{id}/network` - Device network configuration
- **GET** `/api/v1/devices/{id}/system` - Device operating system information
- **GET** `/api/v1/devices/{id}/inventory` - Device asset and identification data
- **GET** `/api/v1/devices/{id}/management` - Device MDM enrollment status
- **GET** `/api/v1/devices/{id}/profiles` - Device configuration profiles
- **GET** `/api/v1/devices/{id}/installs` - Device managed installations

#### Global Module Endpoints (Fleet-Wide Data)
- **GET** `/api/v1/applications` - Application inventory across all devices
- **GET** `/api/v1/hardware` - Hardware inventory report
- **GET** `/api/v1/security` - Security posture overview
- **GET** `/api/v1/network` - Network configuration summary
- **GET** `/api/v1/system` - Operating system distribution
- **GET** `/api/v1/inventory` - Asset management summary
- **GET** `/api/v1/management` - MDM enrollment summary
- **GET** `/api/v1/profiles` - Configuration profiles summary
- **GET** `/api/v1/installs` - Managed installations summary

#### Analytics & Reporting
- **GET** `/api/v1/analytics/summary` - Fleet summary statistics and KPIs
- **GET** `/api/v1/analytics/trends` - Historical trends and forecasting
- **GET** `/api/v1/analytics/compliance` - Compliance reporting and insights

#### Administrative
- **GET** `/api/v1/health` - API health status and diagnostics
- **GET** `/api/v1/metrics` - API performance metrics and statistics
- **GET** `/api/v1/version` - API version and capability information

**Data Processing Modules:**
- `applications` - Installed software and application inventory
- `hardware` - Physical hardware specifications and capabilities
- `inventory` - Asset management and device tracking
- `system` - Operating system information and configuration
- `management` - MDM enrollment and management status
- `security` - Security features, compliance, and vulnerabilities
- `network` - Network interfaces and connectivity
- `profiles` - Configuration profiles and policies
- `installs` - Managed installations (Munki, Cimian, etc.)

## Container Strategy

ReportMate uses a modern container-based approach for the web application:

### Official Container Image
By default, ReportMate deploys the official web application container from GitHub Container Registry:
```
ghcr.io/reportmate/reportmate-app-web:latest
```

This provides:
- ✅ **Complete Next.js frontend** - Full-featured web dashboard
- ✅ **Pre-built and tested** - Production-ready container image
- ✅ **Automatic updates** - Latest features and security patches
- ✅ **Zero build time** - Deploy immediately without compilation
- ✅ **Official support** - Maintained by the ReportMate team

### Custom Container Registry (Optional)
For enterprise environments requiring custom modifications:
```hcl
use_custom_registry = true
container_registry_name = "mycompanyacr"
container_image = "mycompanyacr.azurecr.io/reportmate-web:custom"
```

### Architecture Benefits
- **Separation of Concerns**: Infrastructure code vs. application code
- **Independent Scaling**: Web app and API scale independently
- **Easy Updates**: Update web app without infrastructure changes
- **Multi-Environment**: Same infrastructure, different app versions

### Container Updates

For detailed container update procedures, see [wiki/CONTAINER_UPDATE_GUIDE.md](./wiki/CONTAINER_UPDATE_GUIDE.md).

**Quick update commands:**
```powershell
# Deploy API container
.\scripts\deploy-api.ps1 -ForceBuild

# Deploy frontend container
.\scripts\deploy-containers.ps1 -Environment prod -ForceBuild
```

The update process includes automated health checks, rollback capabilities, and production verification.

## Terraform Module Usage

## Terraform Module Usage

```hcl
module "reportmate" {
  source = "reportmate/reportmate/azurerm"
  
  # Required variables
  resource_group_name = "my-reportmate-rg"
  location           = "East US"
  
  # Database configuration
  db_username = "reportmate_admin"
  db_password = "your-secure-password"
  
  # Optional: Custom domain
  enable_custom_domain = true
  custom_domain_name   = "reportmate.yourdomain.com"
  
  # Container image (defaults to official ReportMate image)
  container_image = "ghcr.io/reportmate/reportmate-app-web:latest"
}
```

## Backend Configuration

This module requires a configured Terraform backend for state storage. Create a `backend.tf` file or use CLI configuration:

```hcl
terraform {
  backend "azurerm" {
    resource_group_name  = "your-terraform-state-rg"
    storage_account_name = "yourterraformstate"
    container_name       = "terraform-state"
    key                  = "reportmate.tfstate"
  }
}
```

Or use CLI initialization:
```bash
terraform init \
  -backend-config="resource_group_name=your-terraform-state-rg" \
  -backend-config="storage_account_name=yourterraformstate" \
  -backend-config="container_name=terraform-state" \
  -backend-config="key=reportmate.tfstate"
```

## Examples

- [Basic Deployment](./examples/basic/) - Simple development setup
- [Production with Custom Domain](./examples/production/) - Production-ready with Front Door
- [Custom Container Registry](./examples/custom-registry/) - Using your own container images

## Module Structure

```
├── main.tf                    # Main module entry point
├── variables.tf              # Input variables
├── outputs.tf               # Output values
├── versions.tf              # Provider requirements
├── backend.tf.example       # Example backend configuration
├── terraform.tfvars.example # Example variables file
├── api/                     # Complete REST API implementation
│   ├── main.tf             # API infrastructure (Azure Functions)
│   ├── variables.tf        # API-specific variables
│   ├── outputs.tf          # API outputs
│   ├── devices/            # GET /api/v1/devices endpoint
│   ├── ingest/             # POST /api/v1/ingest endpoint
│   ├── health/             # GET /api/v1/health endpoint
│   ├── version/            # GET /api/v1/version endpoint
│   ├── device-applications/ # GET /api/v1/devices/{id}/applications
│   ├── device-hardware/    # GET /api/v1/devices/{id}/hardware
│   ├── device-security/    # GET /api/v1/devices/{id}/security
│   ├── device-management/  # GET /api/v1/devices/{id}/management
│   ├── applications/       # GET /api/v1/applications (global)
│   ├── analytics-summary/  # GET /api/v1/analytics/summary
│   ├── processors/         # 9 data processing modules
│   └── shared/             # Shared utilities (auth, database, etc.)
├── modules/
│   ├── containers/         # Azure Container Apps for web frontend
│   ├── database/          # PostgreSQL Flexible Server
│   ├── identity/          # Managed Identity and RBAC
│   ├── messaging/         # Azure Web PubSub for real-time updates
│   ├── monitoring/        # Application Insights and Log Analytics
│   ├── networking/        # Azure Front Door (optional)
│   └── storage/           # Storage Account for functions and data
├── schemas/               # Database schema and migrations
│   ├── schema.prisma     # Master Prisma schema (source of truth)
│   ├── database.sql      # Raw SQL schema
│   └── migrations/       # Database migration scripts
└── examples/             # Example configurations and deployments
    ├── basic/            # Basic single-tenant deployment
    ├── enterprise/       # Multi-tenant enterprise deployment
    └── development/      # Development environment setup
```
│   ├── database/           # PostgreSQL Flexible Server
│   ├── containers/         # Container Apps for web hosting
│   ├── storage/            # Storage Account and containers
│   ├── messaging/          # Web PubSub for real-time features
│   ├── monitoring/         # Application Insights and Log Analytics
│   ├── identity/           # RBAC and managed identities
│   └── networking/         # Front Door and custom domain support
├── schemas/                # Database schemas (Prisma)
├── examples/               # Usage examples
│   ├── basic/             # Simple development setup
│   ├── production/        # Production-ready with custom domain
│   └── complete/          # All features enabled
└── .gitignore             # Terraform and development files
```

## Variables

### Required Variables

| Name | Type | Description |
|------|------|-------------|
| `resource_group_name` | `string` | Name of the Azure resource group to create |
| `location` | `string` | Azure region where resources will be deployed |
| `db_password` | `string` | PostgreSQL administrator password (sensitive) |

### Optional Variables

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `db_username` | `string` | `"reportmate"` | PostgreSQL administrator username |
| `db_name` | `string` | `"reportmate"` | Name of the PostgreSQL database |
| `container_image` | `string` | `"ghcr.io/reportmate/reportmate-app-web:latest"` | Container image for web app |
| `enable_custom_domain` | `bool` | `false` | Enable custom domain with Azure Front Door |
| `custom_domain_name` | `string` | `""` | Custom domain name (e.g., "reportmate.example.com") |
| `environment` | `string` | `"prod"` | Deployment environment (dev, prod, or both) |
| `deploy_dev` | `bool` | `false` | Deploy development container app |
| `deploy_prod` | `bool` | `true` | Deploy production container app |
| `enable_machine_groups` | `bool` | `false` | Enable machine groups for client organization |
| `enable_business_units` | `bool` | `false` | Enable business units for access control |

For a complete list of variables, see [variables.tf](./variables.tf).

See [variables.tf](./variables.tf) for a complete list of configurable options.

### Required Variables

| Name | Type | Description |
|------|------|-------------|
| `resource_group_name` | `string` | Name of the resource group |
| `location` | `string` | Azure region for deployment |
| `db_password` | `string` | PostgreSQL admin password |

### Optional Variables

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `container_image` | `string` | `ghcr.io/reportmate/reportmate-app-web:latest` | Container image to deploy |
| `environment` | `string` | `prod` | Environment name (dev/prod/both) |
| `enable_custom_domain` | `bool` | `false` | Enable custom domain with Front Door |
| `custom_domain_name` | `string` | `""` | Custom domain name |

## Outputs

| Name | Description |
|------|-------------|
| `frontend_url` | URL of the deployed web application |
| `api_url` | URL of the REST API |
| `database_fqdn` | PostgreSQL server FQDN |
| `container_registry_url` | Container registry login server |

## Requirements

- Terraform >= 1.12
- Azure CLI authenticated
- Contributor access to Azure subscription

## 📖 Additional Documentation

For detailed guides and operational documentation, see the [wiki/](./wiki/) directory:

- **[Container Updates](./wiki/CONTAINER_UPDATE_GUIDE.md)** - Production container deployment procedures
- **[Security Best Practices](./wiki/SECURITY.md)** - Security configuration and secrets management
- **[Database Maintenance](./wiki/DATABASE_MAINTENANCE_OPTIONS.md)** - Database optimization and cleanup
- **[Device Archive](./wiki/DEVICE_ARCHIVE_API.md)** - Device lifecycle management
- **[Application Utilization](./wiki/APPLICATION_UTILIZATION_WINDOWS.md)** - Usage tracking features

Full documentation index: [wiki/README.md](./wiki/README.md)

## License

MIT License - see [LICENSE](./LICENSE) for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Support

- Documentation: [ReportMate Docs](https://github.com/reportmate/reportmate)
- Issues: [GitHub Issues](https://github.com/reportmate/terraform-azurerm-reportmate/issues)
- Issues: [GitHub Issues](https://github.com/reportmate/terraform-azurerm-reportmate/issues)
