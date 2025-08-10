# ReportMate Infrastructure Scripts

This directory contains scripts for managing the ReportMate infrastructure and deployments.

## Container Update Scripts

### `update.sh` (Linux/macOS/WSL)
Bash script for updating production containers with full verification and rollback capabilities.

**Usage:**
```bash
# Standard update
./update.sh

# Check current status
./update.sh status

# Show recent logs
./update.sh logs

# Purge Front Door cache only
./update.sh purge-cache

# Manual rollback
./update.sh rollback
```

### `update.ps1` (Windows PowerShell)
PowerShell version of the update script with identical functionality.

**Usage:**
```powershell
# Standard update
.\update.ps1

# Check current status
.\update.ps1 -Action status

# Show recent logs
.\update.ps1 -Action logs

# Purge Front Door cache only
.\update.ps1 -Action purge-cache

# Manual rollback
.\update.ps1 -Action rollback
```

## Other Scripts

### `deploy.ps1`
Infrastructure deployment script using Terraform.

### `bootstrap.ps1`
Initial setup script for development environment.

### `check.ps1`
Health check and validation script for infrastructure.

### `deploy.sh`
Bash version of infrastructure deployment.

## Prerequisites

- Azure CLI (`az`)
- Docker
- Git
- jq (for Bash scripts)
- Appropriate Azure permissions

## Documentation

See `../CONTAINER_UPDATE_GUIDE.md` for detailed documentation on the update process, troubleshooting, and best practices.

## Security Notes

- Scripts require Azure authentication (`az login`)
- Container Registry access is managed via Azure RBAC
- All operations are logged and can be audited through Azure Activity Log
