# SignalR Implementation and Memory Leak Fixes Documentation

## Overview
This document captures all the fixes implemented to resolve browser memory leaks and enable SignalR real-time communication in ReportMate.

## Issues Resolved

### 1. Browser Memory Leaks
**Problem**: Dashboard pages consuming excessive memory and causing browser lockups.

**Root Cause**: 
- Excessive event storage (unlimited growth)
- Aggressive polling intervals (5 seconds)
- Memory leaks from unmanaged React component states

**Solutions Implemented**:
- Limited event storage to 50 events (was unlimited)
- Increased polling interval from 5s to 10s
- Added memory management utilities in `apps/www/app/dashboard/hooks.ts`
- Implemented proper cleanup in useEffect hooks

### 2. SignalR Connection Issues
**Problem**: SignalR showing "Polling" status instead of connecting, despite infrastructure being in place.

**Root Causes**:
1. Missing `/negotiate` endpoint for SignalR authentication
2. Environment variable misconfiguration in Next.js
3. Azure Functions API intermittent 503/500 errors
4. Environment variable name mismatch in negotiate function

**Solutions Implemented**:

#### A. Negotiate Endpoint Creation
- Created `infrastructure/modules/functions/api/negotiate/` directory
- Implemented JWT token generation for Azure WebPubSub authentication
- Added proper CORS headers for cross-origin requests
- Fixed environment variable name from `WebPubSubConnectionString` to `EVENTS_CONNECTION`

#### B. Next.js Environment Variable Configuration
- Fixed `apps/www/next.config.mjs` by removing conflicting env section
- Added proper `NEXT_PUBLIC_` variables in `apps/www/.env.local`:
  ```bash
  NEXT_PUBLIC_ENABLE_SIGNALR=true
  NEXT_PUBLIC_API_BASE_URL=https://reportmate-api.azurewebsites.net
  ```

#### C. Azure Functions Configuration
- Added `WebPubSubConnectionString` environment variable to function app settings
- Maintained existing `EVENTS_CONNECTION` for backward compatibility

## Terraform Configuration Updates

### 1. Azure Web PubSub (Already Configured)
File: `infrastructure/messaging.tf`
```hcl
resource "azurerm_web_pubsub" "wps" {
  name                = "reportmate-signalr"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  
  sku      = "Standard_S1"
  capacity = 1
  
  public_network_access_enabled = true
  local_auth_enabled           = true
}
```

### 2. Function App Settings (Updated)
File: `infrastructure/functions.tf`
```hcl
app_settings = {
  FUNCTIONS_WORKER_RUNTIME               = "python"
  WEBSITE_RUN_FROM_PACKAGE               = "1"
  AZURE_STORAGE_CONNECTION_STRING        = azurerm_storage_account.reportmate.primary_connection_string
  QUEUE_NAME                             = azurerm_storage_queue.ingest.name
  DATABASE_URL                           = "postgresql://${var.db_username}:${var.db_password}@${azurerm_postgresql_flexible_server.pg.fqdn}:5432/${azurerm_postgresql_flexible_server_database.db.name}?sslmode=require"
  EVENTS_CONNECTION                      = azurerm_web_pubsub.wps.primary_connection_string
  WebPubSubConnectionString              = azurerm_web_pubsub.wps.primary_connection_string  # Added for negotiate function
  # ... other settings
}
```

### 3. Variables Configuration
No additional variables needed in `terraform.tfvars.example` - all SignalR configuration is automatically derived from the Azure Web PubSub resource.

## Function Code Updates

### 1. Negotiate Function
File: `infrastructure/modules/functions/api/negotiate/__init__.py`
- Fixed environment variable reference from `WebPubSubConnectionString` to `EVENTS_CONNECTION`
- Implemented proper JWT token generation with device type support
- Added comprehensive error handling and logging

### 2. Frontend Hooks
File: `apps/www/app/dashboard/hooks.ts`
- Added memory leak prevention
- Implemented event count limiting (50 events max)
- Added extensive debugging logs for troubleshooting
- Optimized polling intervals (10 seconds)

## Deployment Steps

### 1. Apply Terraform Changes
```bash
cd infrastructure
terraform plan
terraform apply
```

### 2. Deploy Function App
```bash
cd infrastructure/modules/functions
# Deploy the updated negotiate function
func azure functionapp publish reportmate-api --python
```

### 3. Restart Services
```bash
# Restart function app to pick up new environment variables
az functionapp restart --name reportmate-api --resource-group <resource-group-name>
```

### 4. Verify Frontend Configuration
Ensure `apps/www/.env.local` contains:
```bash
NEXT_PUBLIC_ENABLE_SIGNALR=true
NEXT_PUBLIC_API_BASE_URL=https://reportmate-api.azurewebsites.net
```

## Verification Steps

### 1. Check Azure Web PubSub Service
```bash
az webpubsub show --name reportmate-signalr --resource-group <resource-group-name>
```

### 2. Test Negotiate Endpoint
```bash
curl https://reportmate-api.azurewebsites.net/api/negotiate
```

### 3. Monitor Function App Logs
```bash
az functionapp logs tail --name reportmate-api --resource-group <resource-group-name>
```

### 4. Check Browser Console
- Open ReportMate dashboard
- Check browser console for SignalR connection attempts
- Look for "🔥 useLiveEvents hook called!" messages
- Verify environment variables are accessible

## Current Status

### ✅ Completed
- Azure Web PubSub infrastructure deployed
- Negotiate function created and configured
- Environment variables properly configured
- Memory leak fixes implemented
- Polling optimization completed
- Function app environment variables updated

### ⚠️ In Progress
- SignalR useEffect execution debugging (environment variables accessible but connection logic not executing)
- Azure Functions API stability (intermittent 503/500 errors)

### 🔍 Next Steps
1. Debug why SignalR useEffect isn't executing despite environment variables being accessible
2. Investigate and resolve Azure Functions API intermittent errors
3. Complete SignalR connection implementation
4. Performance testing and optimization

## Resource Names
- **Azure Web PubSub**: `reportmate-signalr`
- **Function App**: `reportmate-api`
- **Resource Group**: As defined in `terraform.tfvars`
- **Hub Name**: `reportmate`

## Environment Variables Reference
- `EVENTS_CONNECTION`: Azure Web PubSub connection string (backend)
- `WebPubSubConnectionString`: Azure Web PubSub connection string (negotiate function compatibility)
- `NEXT_PUBLIC_ENABLE_SIGNALR`: Enable SignalR on frontend
- `NEXT_PUBLIC_API_BASE_URL`: Backend API URL for frontend
