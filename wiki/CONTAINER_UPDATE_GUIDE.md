# ReportMate Production Container Update Guide

This guide documents the complete process for updating the ReportMate container in production, based on real troubleshooting experience and lessons learned.

## Overview

The ReportMate application runs as a containerized Next.js application on Azure Container Apps, served through Azure Front Door CDN. Updates require careful coordination between multiple Azure services to ensure zero downtime and proper cache invalidation.

**🎯 Smart Configuration**: The update scripts automatically discover all Azure resources and load configuration from Terraform outputs, eliminating the need to maintain hardcoded values in multiple places.

## Architecture Components

- **Azure Container Registry (ACR)**: Stores container images (automatically discovered)
- **Azure Container Apps**: Runs the containerized application (automatically discovered)
- **Azure Front Door**: CDN with custom domain (automatically discovered from Terraform outputs)
- **PostgreSQL Database**: Data persistence with fallback from Azure Functions
- **Terraform State**: Source of truth for resource configuration

## Update Process

### Prerequisites

1. **Tools Required**:
   - Azure CLI (`az`)
   - Docker
   - Git
   - Terraform
   - jq (for Bash script only)
   - Bash shell (WSL on Windows, or Linux/macOS) for `.sh` script

2. **Access Required**:
   - Azure subscription with appropriate permissions
   - Access to ReportMate resource group
   - Push access to Azure Container Registry

3. **Repository Setup**:
   - Must be run from the `infrastructure` directory
   - Terraform state must be initialized and applied
   - Dockerfile must exist in `../apps/www/Dockerfile`

4. **Configuration Source**:
   - **Terraform outputs** provide resource group, production URL
   - **Azure resource discovery** finds Container Apps, ACR, Front Door automatically
   - **Resource tagging** helps identify ReportMate-specific resources (Service=reportmate)

### Manual Update Steps

#### 1. Prepare for Update

```bash
# Navigate to infrastructure directory
cd infrastructure

# Verify Terraform state and get current configuration
terraform output

# The script will automatically load:
# - Resource group from: terraform output -raw resource_group_name  
# - Production URL from: terraform output -raw frontend_url
# - Container Apps, ACR, Front Door discovered via Azure CLI queries

# Test current production (optional)
curl -s "$(terraform output -raw frontend_url)/api/version" | jq '.data'
```

#### 2. Build and Push New Image

```bash
# The script handles this automatically, but manual process:

# Generate unique tag
timestamp=$(date +"%Y%m%d%H%M%S")
git_hash=$(git rev-parse --short HEAD)
tag="${timestamp}-${git_hash}"

# Get ACR name from Azure (script does this automatically)
acr_name=$(az acr list --resource-group $(terraform output -raw resource_group_name) --query "[0].name" --output tsv)

# Login to ACR
az acr login --name $acr_name

# Build and push
cd ../apps/www
docker build -t ${acr_name}.azurecr.io/${image_name}:${tag} .
docker push ${acr_name}.azurecr.io/${image_name}:${tag}
cd ../../infrastructure
```

#### 3. Update Container App

```bash
# Get dynamic configuration (script does this automatically)
resource_group=$(terraform output -raw resource_group_name)
container_app=$(az containerapp list --resource-group $resource_group --query "[0].name" --output tsv)
acr_name=$(az acr list --resource-group $resource_group --query "[0].name" --output tsv)

# Get image name from current container app configuration
current_image=$(az containerapp show --resource-group $resource_group --name $container_app --query "properties.template.containers[0].image" --output tsv)
image_name=$(echo "$current_image" | sed 's|.*/\([^:]*\):.*|\1|')

# Update container app with new image
az containerapp update \
  --resource-group $resource_group \
  --name $container_app \
  --image ${acr_name}.azurecr.io/${image_name}:${tag}
  --image ${acr_name}.azurecr.io/reportmate-web:${tag}

# Monitor deployment
az containerapp revision list \
  --resource-group $resource_group \
  --name $container_app \
  --query "reverse(sort_by([?active], &createdTime))[0].{name:name, status:provisioningState, active:active}"
```

#### 4. Verify Container Health

```bash
# Get container FQDN dynamically (script does this automatically)
resource_group=$(terraform output -raw resource_group_name)
container_app=$(az containerapp list --resource-group $resource_group --query "[0].name" --output tsv)
fqdn=$(az containerapp show --resource-group $resource_group --name $container_app \
  --query "properties.configuration.ingress.fqdn" --output tsv)

# Test direct container access
curl -s "https://${fqdn}/api/version" | jq '.success'
curl -s "https://${fqdn}/api/devices" | jq '.success'
```

#### 5. Purge Front Door Cache

```bash
# Get Front Door configuration dynamically (script does this automatically)
resource_group=$(terraform output -raw resource_group_name)
fd_profile=$(az afd profile list --resource-group $resource_group --query "[0].name" --output tsv)
fd_endpoint=$(az afd endpoint list --resource-group $resource_group --profile-name $fd_profile --query "[0].name" --output tsv)

# Purge all cached content
az afd endpoint purge \
  --resource-group $resource_group \
  --profile-name $fd_profile \
  --endpoint-name $fd_endpoint \
  --content-paths "/*"

# Wait for propagation
sleep 30
```

#### 6. Verify Production

```bash
# Get production URL from Terraform (script does this automatically)
production_url=$(terraform output -raw frontend_url)

# Test production URL
curl -s "${production_url}/api/version" | jq '.success'
curl -s "${production_url}/api/devices" | jq '.success'

# Check logs if needed (using discovered resource names)
resource_group=$(terraform output -raw resource_group_name)
container_app=$(az containerapp list --resource-group $resource_group --query "[0].name" --output tsv)
az containerapp logs show --resource-group $resource_group --name $container_app --follow false --tail 20
```

### Automated Update Script

Use the provided `update.sh` script for automated updates:

```bash
# Standard update
./scripts/update.sh

# Check status only
./scripts/update.sh status

# Show recent logs
./scripts/update.sh logs

# Purge cache only
./scripts/update.sh purge-cache

# Manual rollback
./scripts/update.sh rollback
```

## Dynamic Configuration System

The update scripts use a smart configuration system that eliminates hardcoded values:

### Configuration Sources

1. **Terraform Outputs** (primary source):
   ```bash
   # Resource group name
   resource_group=$(terraform output -raw resource_group_name)
   
   # Production URL  
   production_url=$(terraform output -raw frontend_url)
   ```

2. **Azure Resource Discovery** (automatic discovery):
   ```bash
   # Container App (prefers tagged resources)
   container_app=$(az containerapp list --resource-group $resource_group \
     --query "[?contains(tags.Service, 'reportmate')].name | [0]" --output tsv)
   
   # Azure Container Registry
   acr_name=$(az acr list --resource-group $resource_group \
     --query "[?contains(tags.Service, 'reportmate')].name | [0]" --output tsv)
   
   # Image Name (extracted from current container configuration)
   current_image=$(az containerapp show --resource-group $resource_group \
     --name $container_app --query "properties.template.containers[0].image" --output tsv)
   image_name=$(echo "$current_image" | sed 's|.*/\([^:]*\):.*|\1|')
   
   # Front Door Profile and Endpoint
   fd_profile=$(az afd profile list --resource-group $resource_group \
     --query "[?contains(tags.Service, 'reportmate')].name | [0]" --output tsv)
   ```

3. **Fallback Discovery** (when tags not available):
   - If no tagged resources found, uses first available resource of each type
   - Ensures compatibility with various deployment scenarios

### Benefits

- ✅ **No duplicate configuration** - single source of truth in Terraform
- ✅ **Environment agnostic** - works with any resource naming scheme  
- ✅ **Auto-discovery** - finds resources automatically via Azure CLI
- ✅ **Tag-aware** - prefers properly tagged resources
- ✅ **Resilient fallback** - works even without proper tagging
- ✅ **Error handling** - validates all discovered resources before proceeding

## Troubleshooting

### Common Issues

#### 1. Front Door Cache Issues
**Symptom**: Old responses still served after deployment
**Solution**: 
- Verify Front Door origin configuration points to Container App FQDN
- Use specific cache purge paths: `/api/*`
- Wait 5-15 minutes for propagation

#### 2. API Field Name Mismatches
**Symptom**: `{"success": false, "error": "'id'"}`
**Solution**: 
- Check database field names vs. API transformation code
- Ensure compatibility between camelCase (database) and expected formats
- Review logs for Azure Functions vs. database fallback behavior

#### 3. Container App Not Starting
**Symptom**: Deployment stuck or failing
**Solution**:
- Check container logs for startup errors
- Verify environment variables are correctly set
- Ensure Docker image builds successfully locally

#### 4. Front Door Origin Misconfiguration
**Symptom**: 404 errors or serving from wrong backend
**Solution**:
```bash
# Check current origin configuration
az afd origin list --resource-group Reportmate \
  --profile-name reportmate-frontdoor \
  --origin-group-name reportmate-api-origin-group

# Update if needed
az afd origin update --resource-group Reportmate \
  --profile-name reportmate-frontdoor \
  --origin-group-name reportmate-api-origin-group \
  --origin-name reportmate-api-origin \
  --host-name "reportmate-container-prod.blackdune-79551938.canadacentral.azurecontainerapps.io" \
  --origin-host-header "reportmate-container-prod.blackdune-79551938.canadacentral.azurecontainerapps.io"
```

### Recovery Procedures

#### Rollback to Previous Revision

```bash
# List recent revisions
az containerapp revision list --resource-group Reportmate \
  --name reportmate-container-prod \
  --query "reverse(sort_by([?active], &createdTime))[0:3].{name:name, active:active, created:createdTime}"

# Activate previous revision
az containerapp revision activate --resource-group Reportmate \
  --name reportmate-container-prod \
  --revision <previous-revision-name>
```

#### Emergency Cache Bypass

```bash
# Test with cache bypass
curl -s "https://reportmate.ecuad.ca/api/devices?nocache=$(date +%s)" | jq '.success'
```

## Monitoring

### Key Endpoints to Monitor

1. **Health Check**: `https://reportmate.ecuad.ca/api/version`
2. **Data API**: `https://reportmate.ecuad.ca/api/devices`
3. **Direct Container**: `https://<container-fqdn>/api/version`

### Log Analysis

```bash
# Container logs
az containerapp logs show --resource-group Reportmate \
  --name reportmate-container-prod --follow false --tail 50

# Look for these patterns:
# - "Azure Functions API error: 500" (expected, triggers fallback)
# - "Local database fallback successful" (good)
# - "Using API base URL" (shows which backend is being used)
```

## Best Practices

1. **Always test direct container access** before purging cache
2. **Use specific cache purge paths** (`/api/*`) rather than global (`/*`)
3. **Monitor deployment status** before proceeding to next step
4. **Keep previous revision active** until verification complete
5. **Document any configuration changes** made during troubleshooting

## Version Display Feature

The container includes a version display feature accessible via `/settings`:
- Shows container version, build ID, build time
- Useful for verifying successful deployments
- Implemented in `VersionDisplay.tsx` component

## Environment Configuration

Key environment variables:
- `API_BASE_URL`: Azure Functions endpoint (with fallback to local DB)
- `DATABASE_URL`: PostgreSQL connection for fallback
- `NODE_ENV`: Production environment setting

## Security Considerations

- Container Registry access is secured via Azure RBAC
- Front Door provides HTTPS termination and custom domain
- Database fallback ensures service availability even with Azure Functions issues

---

*This guide was developed through real production troubleshooting and includes lessons learned from actual deployment challenges.*
