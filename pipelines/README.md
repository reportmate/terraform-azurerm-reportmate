# ReportMate Pipelines (samples)

These are sample Azure DevOps pipelines derived from a working production deployment of this module. They are starting points: copy them into your own repository and replace every `<placeholder>` and default name with your values before running them.

| File                                                           | Purpose                                                                                                                                        |
| -------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| [`deploy.azure-pipelines.yaml`](./deploy.azure-pipelines.yaml) | Mirrors the published images into your ACR, applies Terraform, rolls both container apps, purges Front Door and checks health. Manual trigger. |
| [`plan.azure-pipelines.yaml`](./plan.azure-pipelines.yaml)     | Init, validate and a read-only `terraform plan`. Use it as a pull request check. Never applies.                                                |

## What the deploy pipeline does

1. **Mirror images** - `az acr import` copies `ghcr.io/reportmate/reportmate-app-web` and `ghcr.io/reportmate/reportmate-api` into your registry with a timestamped tag. No Docker daemon is needed on the agent.
2. **Terraform plan and apply** - runs against your remote state with `-var="frontend_image_tag=..."` and `-var="api_image_tag=..."`.
3. **Roll container apps** - the containers module ignores image changes on purpose, so the pipeline pushes the new tags with `az containerapp update`.
4. **Health checks** - polls the API `/api/v1/health` endpoint, purges Front Door and polls the custom domain.

## Setup

1. Create an Azure Resource Manager service connection that uses workload identity federation. The identity needs Contributor on the ReportMate resource group, AcrPush on the registry, and Storage Blob Data Contributor on the Terraform state container.
2. Create a variable group named `reportmate-secrets` with secret variables `DbPassword`, `ClientPassphrase`, `NextAuthSecret`, `ApiInternalSecret` and `KioskTokens`. Terraform writes them into Key Vault on apply.
3. Create the non-secret var file the pipelines read (`reportmate.prod.tfvars` by default), starting from [`terraform.tfvars.example`](../terraform.tfvars.example). This repository ignores `*.tfvars`, so in your own private repository either un-ignore that one file or keep it in a secure file.
4. Edit the `variables` block in each YAML: service connection name, resource group, registry, container app names, API URL, Front Door names, custom domain and Terraform backend.
5. Create one pipeline per YAML in Azure DevOps. To gate pull requests, add a build-validation branch policy on `main` that runs the plan pipeline; Azure Repos ignores YAML `pr` triggers.

## Terraform backend

Both pipelines pass a partial backend configuration at `terraform init`:

- Resource group: `<your-terraform-state-rg>`
- Storage account: `<your-terraform-state-storage>`
- Container: `terraform-state`
- Key: `reportmate.tfstate`

Keep these values identical in both pipelines and in your local `backend.tf`.

## Troubleshooting

- **Image import fails** - check the source tag exists in GHCR and the identity has AcrPush on the registry.
- **Terraform init fails with an authorization error** - the identity needs a data-plane role on the state container, not only Contributor on the storage account.
- **Health check fails** - container apps can need more warmup time; check the revision logs in the Azure portal and DNS for the custom domain.
