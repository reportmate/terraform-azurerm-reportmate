# ReportMate Infrastructure

Clean, organized infrastructure management for ReportMate.

## Quick Start

### Deploy Everything
```powershell
.\scripts\deploy-all.ps1
```

### Deploy Individual Components

**Azure Functions Only:**
```powershell
.\modules\functions\deploy.ps1
```

**Database Migrations Only:**
```powershell
.\database\migrate.ps1
```

**Container Updates:**
```powershell
.\scripts\update-container.ps1 -Frontend
```

### Check Status
```powershell
.\scripts\status.ps1
```

## Directory Structure

```
infrastructure/
├── database/           # Database migrations
│   ├── migrate.ps1    # Run all migrations
│   ├── 001_initial_schema.sql
│   ├── 002_add_modules.sql
│   └── 003_add_indexes.sql
├── modules/
│   └── functions/     # Azure Functions
│       ├── deploy.ps1 # Deploy functions with vendored deps
│       └── api/       # Function code
├── scripts/           # Infrastructure scripts
│   ├── deploy-all.ps1     # Deploy everything
│   ├── status.ps1         # Check system status
│   ├── update-container.ps1  # Update containers
│   ├── deploy-auth.ps1    # Auth setup
│   └── deploy-containers.ps1 # Container deployment
└── *.tf              # Terraform configuration
```

## Core Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `deploy-all.ps1` | Deploy entire infrastructure | `.\scripts\deploy-all.ps1` |
| `status.ps1` | Check all components status | `.\scripts\status.ps1` |
| `functions\deploy.ps1` | Deploy Azure Functions | `.\modules\functions\deploy.ps1` |
| `database\migrate.ps1` | Run database migrations | `.\database\migrate.ps1` |
| `update-container.ps1` | Update container apps | `.\scripts\update-container.ps1 -Frontend` |

## API Endpoints

- **Health:** https://reportmate-api.azurewebsites.net/api/health
- **Debug:** https://reportmate-api.azurewebsites.net/api/debug  
- **Devices:** https://reportmate-api.azurewebsites.net/api/devices
- **Events:** https://reportmate-api.azurewebsites.net/api/events

## Database

PostgreSQL Flexible Server with these tables:
- `devices` - Device registry
- `events` - System events
- `applications`, `hardware`, `network`, etc. - Module data

## Notes

- **Azure Functions:** Uses vendored dependencies (packages in `.python_packages`)
- **Database:** Auto-migration system with SQL files
- **Containers:** Azure Container Apps with auto-scaling
- **Deployment:** All scripts are idempotent and safe to re-run
