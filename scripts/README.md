# ReportMate Infrastructure Scripts

Sample operational scripts for a ReportMate deployment. Adapt parameters and names to your environment before use. Deploying images is the job of the [sample deploy pipeline](../pipelines/README.md).

## Scripts Overview

- **check.ps1** - Comprehensive system health check and validation
- **deploy-maintenance.ps1** / **deploy-maintenance.sh** - Deploy the database maintenance jobs
- **setup-local-env.ps1** - Restore local environment files from Key Vault
- **migrate-secrets.ps1** - Rename Key Vault secrets and update container app references
- **status.ps1** - Quick status check of all infrastructure components

## Usage

Run a complete system health check:

```powershell
.\check.ps1
```

Show a quick status of all components:

```powershell
.\status.ps1
```

## Architecture

- **FastAPI Container**: Backend API with database operations
- **Next.js Container**: Frontend web application  
- **PostgreSQL**: Azure Database for device and event data