# ReportMate Azure Terraform Module

![ReportMate](https://img.shields.io/badge/ReportMate-v1.0-blue)
![Terraform](https://img.shields.io/badge/Terraform-%3E%3D1.12-purple)
![Azure](https://img.shields.io/badge/Azure-Cloud-blue)

A comprehensive Terraform module for deploying ReportMate infrastructure on Azure. This module provisions a complete osquery fleet management platform with web interface, API, real-time messaging, and monitoring.

## Directory Structure

```
infrastructure/azure/
├── main.tf                 # Primary infrastructure definition
├── variables.tf            # Input variables
├── outputs.tf              # Output values
├── versions.tf             # Provider and version constraints
├── backend.tf              # State backend configuration (gitignored)
├── terraform.tfvars        # Deployment variables (gitignored)
├── modules/                # Reusable Terraform modules
│   ├── api/                # FastAPI container application
│   │   ├── main.py         # FastAPI application (4300+ lines)
│   │   ├── Dockerfile      # Container build definition
│   │   ├── requirements.txt
│   │   ├── sql/            # External SQL queries (43 files)
│   │   │   ├── devices/    # Device query files
│   │   │   ├── events/     # Event query files
│   │   │   ├── admin/      # Admin operation queries
│   │   │   └── tests/      # pgAdmin test wrappers
│   │   └── scripts/        # API utility scripts
│   ├── auth/               # Authentication module
│   ├── containers/         # Container Apps module
│   ├── database/           # PostgreSQL database module
│   ├── functions/          # Azure Functions (deprecated)
│   ├── identity/           # Managed Identity module
│   ├── key_vault/          # Key Vault module
│   ├── maintenance/        # Database maintenance jobs
│   ├── messaging/          # Web PubSub module
│   ├── monitoring/         # Application Insights module
│   ├── networking/         # Front Door module
│   └── storage/            # Azure Storage module
├── scripts/                # Deployment and utility scripts
├── schemas/                # Database schemas and migrations
├── pipelines/              # CI/CD pipeline definitions
└── wiki/                   # Detailed documentation and guides
```

For detailed documentation, see [wiki/README.md](./wiki/README.md)

## Quick Start

### Prerequisites

**Required Tools:**
- **Azure CLI**: `winget install Microsoft.AzureCLI` or [Download](https://learn.microsoft.com/cli/azure/install-azure-cli)
- **Terraform**: `winget install Hashicorp.Terraform` or [Download](https://www.terraform.io/downloads)
- **PowerShell 7+**: `winget install Microsoft.PowerShell` (for scripts)
- **Docker**: Required for container builds

**Azure Authentication:**
```powershell
az login
az account set --subscription "<your-subscription-id>"
az account show  # Verify your account
```

### Bootstrap Deployment (Recommended)

For a fresh deployment, use the canonical bootstrap script:

```powershell
# Complete bootstrap (infrastructure + database + containers)
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

## Deployment Scripts

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

- **Web Application**: Next.js frontend with real-time dashboard and modular architecture
- **REST API**: FastAPI container with external SQL queries and comprehensive endpoints
- **Database**: PostgreSQL for storing osquery results and configurations
- **Real-time Messaging**: Azure Web PubSub for live fleet updates
- **Container Platform**: Azure Container Apps for scalable hosting
- **Monitoring**: Application Insights for observability and analytics
- **Security**: Machine group authentication and managed identities

### REST API Endpoints

The FastAPI application (`modules/api/main.py`) provides these endpoint categories:

#### Health and Status
- **GET** `/api/health` - API health status and database connectivity
- **GET** `/api/docs` - Interactive OpenAPI documentation

#### Device Management
- **GET** `/api/devices` - List all devices with filtering
- **GET** `/api/device/{serial}` - Get device with all module data
- **POST** `/api/events` - Ingest device telemetry data
- **POST** `/api/device/{serial}/archive` - Archive a device
- **POST** `/api/device/{serial}/unarchive` - Restore archived device
- **DELETE** `/api/device/{serial}` - Permanently delete device

#### Bulk Fleet Endpoints
- **GET** `/api/devices/hardware` - Hardware inventory across fleet
- **GET** `/api/devices/installs` - Managed installations fleet-wide
- **GET** `/api/devices/network` - Network configuration summary
- **GET** `/api/devices/security` - Security posture overview
- **GET** `/api/devices/profiles` - Configuration profiles summary
- **GET** `/api/devices/management` - MDM enrollment summary
- **GET** `/api/devices/inventory` - Asset management summary
- **GET** `/api/devices/system` - Operating system distribution
- **GET** `/api/devices/peripherals` - Displays and printers

#### Events
- **GET** `/api/events` - List events with filtering
- **GET** `/api/events/{id}` - Get specific event
- **GET** `/api/events/{id}/payload` - Get event raw payload

#### Dashboard
- **GET** `/api/dashboard` - Aggregated dashboard data

### SQL Query Architecture

SQL queries are externalized to `.sql` files for maintainability:

```
modules/api/sql/
├── devices/           # 20 device query files
│   ├── bulk_hardware.sql
│   ├── bulk_installs.sql
│   ├── list_devices.sql
│   └── ...
├── events/            # 3 event query files
├── admin/             # 8 admin operation files
└── tests/             # 12 pgAdmin test wrappers
```

Benefits:
- Test queries directly in pgAdmin
- Syntax highlighting in SQL editors
- Version control friendly diffs
- Security: Path traversal validation
- Performance: Queries preloaded at startup

### Data Processing Modules

ReportMate processes 11 data modules from client telemetry:

| Module | Description |
|--------|-------------|
| `applications` | Installed software inventory |
| `hardware` | Physical hardware specifications |
| `inventory` | Asset management and device tracking |
| `system` | Operating system information |
| `management` | MDM enrollment status |
| `security` | Security features and compliance |
| `network` | Network interfaces and connectivity |
| `profiles` | Configuration profiles and policies |
| `installs` | Managed installations (Munki, Cimian) |
| `displays` | Connected display information |
| `printers` | Connected printer information |

## Container Strategy

ReportMate uses Azure Container Apps for both API and frontend:

### API Container
- **Image**: Built from `modules/api/Dockerfile`
- **Registry**: Azure Container Registry (reportmateacr.azurecr.io)
- **Deployment**: `.\scripts\deploy-api.ps1 -ForceBuild`

### Frontend Container
- **Image**: `ghcr.io/reportmate/reportmate-app-web:latest` (default)
- **Registry**: GitHub Container Registry or custom ACR
- **Deployment**: `.\scripts\deploy-containers.ps1 -Environment prod -ForceBuild`

### Custom Container Registry (Optional)
For enterprise environments requiring custom modifications:
```hcl
use_custom_registry = true
container_registry_name = "mycompanyacr"
container_image = "mycompanyacr.azurecr.io/reportmate-web:custom"
```

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

This module requires a configured Terraform backend for state storage:

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

## Variables

### Required Variables

| Name | Type | Description |
|------|------|-------------|
| `resource_group_name` | `string` | Name of the Azure resource group |
| `location` | `string` | Azure region for deployment |
| `db_password` | `string` | PostgreSQL administrator password (sensitive) |

### Optional Variables

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `db_username` | `string` | `"reportmate"` | PostgreSQL administrator username |
| `db_name` | `string` | `"reportmate"` | Name of the PostgreSQL database |
| `container_image` | `string` | `"ghcr.io/reportmate/reportmate-app-web:latest"` | Container image for web app |
| `enable_custom_domain` | `bool` | `false` | Enable custom domain with Azure Front Door |
| `custom_domain_name` | `string` | `""` | Custom domain name |
| `environment` | `string` | `"prod"` | Deployment environment (dev, prod) |

See [variables.tf](./variables.tf) for complete list.

## Outputs

| Name | Description |
|------|-------------|
| `frontend_url` | URL of the deployed web application |
| `api_url` | URL of the FastAPI container |
| `database_fqdn` | PostgreSQL server FQDN |
| `container_registry_url` | Container registry login server |

## Requirements

- Terraform >= 1.12
- Azure CLI authenticated
- Docker (for container builds)
- Contributor access to Azure subscription

## Additional Documentation

For detailed guides and operational documentation, see the [wiki/](./wiki/) directory:

- **[Container Updates](./wiki/CONTAINER_UPDATE_GUIDE.md)** - Production container deployment procedures
- **[Security Best Practices](./wiki/SECURITY.md)** - Security configuration and secrets management
- **[Database Maintenance](./wiki/DATABASE_MAINTENANCE_OPTIONS.md)** - Database optimization and cleanup
- **[Device Archive](./wiki/DEVICE_ARCHIVE_API.md)** - Device lifecycle management

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
