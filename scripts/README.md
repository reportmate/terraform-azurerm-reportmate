# ReportMate Deployment Scripts

This directory contains deployment and utility scripts for ReportMate infrastructure.

## Scripts

### `deploy.ps1` (PowerShell)
Cross-platform PowerShell deployment script that supports:
- Complete infrastructure deployment (Terraform + Functions)
- Quick function-only deployments
- Environment-specific deployments (dev, staging, prod)

**Usage:**
```powershell
# Full deployment
./deploy.ps1 -Environment prod

# Quick function-only deployment
./deploy.ps1 -Quick

# Infrastructure only
./deploy.ps1 -Infrastructure

# Auto-approve without prompts
./deploy.ps1 -Yes
```

### `deploy.sh` (Bash)
Linux/macOS bash deployment script with similar functionality to the PowerShell version.

**Usage:**
```bash
# Full deployment
./deploy.sh --env prod

# Quick function-only deployment
./deploy.sh --quick

# Infrastructure only
./deploy.sh --infra

# Auto-approve without prompts
./deploy.sh --yes
```

## Prerequisites

- Azure CLI installed and authenticated
- Terraform installed (for infrastructure deployment)
- PowerShell Core (for .ps1 script on non-Windows)

## Working Directory

These scripts should be run from the repository root directory. They will automatically navigate to the appropriate subdirectories (`infrastructure/terraform/` for Terraform operations).
