# ReportMate Infrastructure - Quick Start Guide

## 🚀 Complete Bootstrap (Recommended)

For a fresh deployment, use the canonical bootstrap script:

```powershell
# Clone repository
git clone https://github.com/reportmate/reportmate-app-web.git
cd reportmate-app-web

# Complete bootstrap (infrastructure + database + functions)
.\infrastructure\scripts\bootstrap.ps1

# With auto-approval for CI/CD
.\infrastructure\scripts\bootstrap.ps1 -AutoApprove -Validate
```

## 🔍 Health Monitoring

Use the canonical health check script for ongoing monitoring:

```powershell
# Basic health check
.\infrastructure\scripts\check.ps1

# Detailed diagnostic output
.\infrastructure\scripts\check.ps1 -DetailedOutput -TestData

# Check and attempt to fix issues
.\infrastructure\scripts\check.ps1 -FixIssues
```

## 📋 Manual Deployment Steps

If you need to deploy components individually:

### 1. Prerequisites

```powershell
# Install required tools
# - Azure CLI: winget install Microsoft.AzureCLI
# - Terraform: winget install Hashicorp.Terraform
# - PowerShell 7+: winget install Microsoft.PowerShell

# Login to Azure
az login
```

### 2. Configure Terraform Backend

```powershell
cd infrastructure

# One-time setup: Create storage account for Terraform state
az group create --name Terraform --location canadacentral
az storage account create --name youruniquename --resource-group Terraform --sku Standard_LRS --encryption-services blob
az storage container create --name terraform-state --account-name youruniquename

# Create your backend.tf from the example
Copy-Item backend.tf.example backend.tf

# Edit backend.tf with your storage account details
# NOTE: backend.tf is gitignored - never commit it to source control
```

### 3. Infrastructure (Terraform)

```powershell
cd infrastructure

# Copy and configure variables
Copy-Item terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values

# Initialize with backend
terraform init

# Deploy infrastructure
terraform plan -out=tfplan
terraform apply tfplan
```

### 4. Database Schema

```powershell
# Initialize database schema via API
curl "https://reportmate-functions-api.blackdune-79551938.canadacentral.azurecontainerapps.io/api/init-db?init=true"

# Or manually via psql
psql "postgresql://reportmate:PASSWORD@reportmate-database.postgres.database.azure.com:5432/reportmate?sslmode=require" -f schemas/database.sql
```

### 5. Container Apps Deployment

```powershell
cd infrastructure/scripts

# Deploy Container Apps (API + Frontend)
.\deploy-containers.ps1
```

## 🏗️ Architecture Overview

### Database Structure

**Modular Architecture** - One table per JSON module from Windows client:

```
📊 Core Tables:
├── devices        # Master device registry (serial number as PK)
└── events         # Activity logs and errors

📦 Modular Tables (1 per JSON module):
├── applications   # Installed software
├── displays       # Monitor/display info
├── hardware       # CPU, memory, storage
├── installs       # Installation history
├── inventory      # Asset inventory
├── management     # MDM/management info
├── network        # Network configuration
├── printers       # Printer devices
├── profiles       # Configuration profiles
├── security       # Security features/status
└── system         # OS and system info
```

### API Endpoints

```
🌐 Production API: https://reportmate-api.azurewebsites.net

📋 Core Endpoints:
├── GET  /api/health         # Health check
├── GET  /api/devices        # List all devices
├── GET  /api/device/{id}    # Single device details
├── GET  /api/events         # Recent events
├── POST /api/events-submit  # Data submission from clients
└── GET  /api/init-db?init=true  # Database initialization
```

### Data Flow

```
Windows Client (managedreportsrunner.exe)
    ↓ [HTTPS POST]
Azure Functions API (/api/events-submit)
    ↓ [Validate & Process]
PostgreSQL Database (Modular Tables)
    ↓ [Query]
Web Interface (Next.js)
```

## 🔧 Configuration

### Environment Variables

```powershell
# Set in Azure Function App settings
DATABASE_URL=postgresql://reportmate:PASSWORD@reportmate-database.postgres.database.azure.com:5432/reportmate?sslmode=require
ENVIRONMENT=dev|staging|prod
LOG_LEVEL=INFO|DEBUG
```

### Client Configuration

```powershell
# Windows client configuration (managedreportsrunner.exe)
managedreportsrunner.exe config --api-url https://reportmate-api.azurewebsites.net
managedreportsrunner.exe test  # Test connectivity
```

## 🐛 Troubleshooting

### Database Connection Issues

```powershell
# Test database connectivity
psql "postgresql://reportmate:PASSWORD@reportmate-database.postgres.database.azure.com:5432/reportmate?sslmode=require" -c "SELECT 1;"

# Check firewall rules
az postgres flexible-server firewall-rule list --name reportmate-database --resource-group ReportMate
```

### API Issues

```powershell
# Test API endpoints
curl https://reportmate-api.azurewebsites.net/api/health
curl https://reportmate-api.azurewebsites.net/api/devices

# Check function logs
az functionapp logs tail --name reportmate-api --resource-group ReportMate
```

### Client Issues

```powershell
# Test client connectivity
managedreportsrunner.exe test

# View client logs
Get-Content "C:\ProgramData\ManagedReports\logs\reportmate.log" -Tail 50

# Reset client configuration
managedreportsrunner.exe config --reset
```

## 📊 Monitoring Commands

### Quick Status Check

```powershell
# Run canonical health check
.\infrastructure\scripts\check.ps1

# Expected output:
# ✅ Database Connection
# ✅ API Endpoints  
# ✅ Database Schema
# ✅ Data Integrity
# ✅ Event Processing
# 🎯 OVERALL STATUS: HEALTHY
```

### Database Statistics

```sql
-- Connect to database
\c postgresql://reportmate:PASSWORD@reportmate-database.postgres.database.azure.com:5432/reportmate?sslmode=require

-- View table sizes
SELECT 
    schemaname,
    tablename,
    pg_total_relation_size(schemaname||'.'||tablename) as size_bytes,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname = 'public' 
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- View record counts
SELECT 'devices' as table_name, COUNT(*) as count FROM devices
UNION ALL SELECT 'events', COUNT(*) FROM events
UNION ALL SELECT 'applications', COUNT(*) FROM applications
UNION ALL SELECT 'hardware', COUNT(*) FROM hardware;
```

## 🚨 Emergency Procedures

### Complete Reset

```powershell
# ⚠️  WARNING: This destroys all data!

# 1. Destroy infrastructure
cd infrastructure
terraform destroy -auto-approve

# 2. Clean bootstrap
.\scripts\bootstrap.ps1 -AutoApprove

# 3. Validate
.\scripts\check.ps1 -Validate
```

### Database Only Reset

```powershell
# Clear all data but keep schema
curl "https://reportmate-api.azurewebsites.net/api/cleanup-db?confirm=yes"

# Reinitialize schema
curl "https://reportmate-api.azurewebsites.net/api/init-db?init=true"
```

## 📞 Support

- **Documentation**: `docs/` directory
- **Health Check**: `.\infrastructure\scripts\check.ps1`
- **Bootstrap**: `.\infrastructure\scripts\bootstrap.ps1`
- **Issues**: GitHub Issues
- **Logs**: Azure Portal → Function App → Log Stream

---

✨ **The system is designed to be self-contained and bootstrapped with minimal manual intervention.**
