# ReportMate Infrastructure Scripts

Essential deployment and management scripts for ReportMate.

## Scripts Overview

- **check.ps1** - Comprehensive system health check and validation
- **deploy-containers.ps1** - Deploy frontend Next.js container
- **status.ps1** - Quick status check of all infrastructure components

## Usage

```powershell
# Complete system health check
.\check.ps1

# Quick status of all components  
.\status.ps1

# Deploy API backend
# Deploying is the pipeline's job - see pipelines/README.md

# Deploy frontend application
.\deploy-containers.ps1
```

## Architecture

- **FastAPI Container**: Backend API with database operations
- **Next.js Container**: Frontend web application  
- **PostgreSQL**: Azure Database for device and event data