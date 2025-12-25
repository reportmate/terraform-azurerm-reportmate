# ReportMate Infrastructure Pipelines

This directory contains CI/CD pipeline templates for deploying ReportMate infrastructure and containers.

## Pipeline Options

| File | Platform | Description |
|------|----------|-------------|
| `infra-deployment-github.yaml` | GitHub Actions | Full CI/CD for GitHub repositories |
| `infra-deployment-devops.yaml` | Azure DevOps | Full CI/CD for Azure DevOps repositories |

## What These Pipelines Do

Both pipelines replicate the functionality of the development scripts (`deploy-api.ps1` and `deploy-app.ps1`) in a CI/CD context, making **Terraform the single source of truth**.

### Pipeline Stages

1. **Terraform Plan** - Validates infrastructure changes, comments on PRs
2. **Build Containers** - Builds frontend and API Docker images with proper tags
3. **Terraform Apply** - Applies infrastructure changes
4. **Deploy Containers** - Updates container apps with new images
5. **Purge CDN** - Clears Azure Front Door cache
6. **Health Check** - Validates deployment success

### Triggers

- **Push to main**: Full deployment
- **Pull Request**: Plan only (no apply)
- **Manual dispatch**: Choose what to deploy

## Setup Instructions

### GitHub Actions

1. Copy `infra-deployment-github.yaml` to `.github/workflows/`
2. Create repository secrets:
   - `AZURE_CREDENTIALS` - Service principal JSON with contributor access

```json
{
  "clientId": "<app-id>",
  "clientSecret": "<password>",
  "subscriptionId": "<subscription-id>",
  "tenantId": "<tenant-id>"
}
```

3. Create environment named `production` with required reviewers (optional)

### Azure DevOps

1. Create a new pipeline pointing to `infrastructure/pipelines/infra-deployment-devops.yaml`
2. Create service connection named `ReportMate-ServiceConnection`
3. Create environment named `Production` with approval gates (optional)

## Key Features

### Build Tags
Both pipelines generate consistent tags:
- **Frontend**: `YYYYMMDDHHMMSS-<git-hash>`
- **API**: `device-id-fix-YYYYMMDDHHMMSS-<git-hash>`

### Environment Variables Updated
Frontend container receives build metadata:
- `CONTAINER_IMAGE_TAG`
- `BUILD_TIME`
- `BUILD_ID`
- `NEXT_PUBLIC_VERSION`
- `NEXT_PUBLIC_BUILD_ID`
- `NEXT_PUBLIC_BUILD_TIME`

### Terraform Backend
Both pipelines use a shared backend configuration:
- Resource Group: `<your-terraform-backend-rg>`
- Storage Account: `<your-terraform-backend-storage>`
- Container: `terraform-state`
- Key: `reportmate.tfstate`

> **Note:** Replace the placeholders above with your actual Terraform backend configuration values.

## Manual Deployment Options

### Force Rebuild (no cache)
Use when you need a clean build:
- GitHub: Set `force_build: true` in workflow dispatch
- DevOps: Check "Force Rebuild (no cache)" parameter

### Selective Deployment
Deploy only frontend or API:
- GitHub: Set `deploy_frontend` or `deploy_api` to false
- DevOps: Uncheck the respective checkbox

## Migrating from Scripts

The pipelines replace these development scripts:

| Script | Pipeline Stage |
|--------|---------------|
| `deploy-app.ps1` | Build Containers + Deploy Frontend |
| `deploy-api.ps1` | Build Containers + Deploy API |
| `deploy-app.ps1 -PurgeOnly` | Purge CDN |

The scripts remain available for local development and debugging.

## Troubleshooting

### Container Build Fails
- Check Dockerfile paths are correct
- Verify ACR login succeeds
- Check build args are properly passed

### Terraform Apply Fails
- Review plan output for unexpected changes
- Check state file isn't locked
- Verify service principal has required permissions

### Health Check Fails
- Containers may need more warmup time
- Check container logs in Azure portal
- Verify DNS propagation for custom domain
