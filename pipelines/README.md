# ReportMate Pipelines (samples)

These are sample Azure DevOps pipelines derived from a working production deployment of this module. They are starting points: copy them into your own repository and replace every `<placeholder>` and default name with your values before running them.

| File                                                           | Purpose                                                                                                                                        |
| -------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| [`deploy.azure-pipelines.yaml`](./deploy.azure-pipelines.yaml) | Plans, then after approval mirrors the published images into your ACR, applies Terraform, rolls both container apps, purges Front Door and checks health. Manual trigger, `main` only. |
| [`plan.azure-pipelines.yaml`](./plan.azure-pipelines.yaml) | Init, validate and a read-only `terraform plan` with read-only credentials and no secrets. Use it as a pull request check. Never applies. |

## What the deploy pipeline does

1. **Plan stage** - fails unless the run is on `refs/heads/main`, validates both image tags against `^[A-Za-z0-9._-]{1,128}$` (and rejects `latest`), and prints the Terraform plan for review.
2. **Approval** - the Deploy stage is a deployment job against the `reportmate-production` environment, so it waits for that environment's approvals and checks.
3. **Mirror images** - `az acr import` copies the requested release tags of `ghcr.io/reportmate/reportmate-app-web` and `ghcr.io/reportmate/reportmate-api` into your registry as `<tag>-<build-id>`. Nothing is overwritten and no `:latest` tag is written.
4. **Terraform apply** - re-plans and applies with the new image tags.
5. **Roll container apps** - the containers module ignores image changes on purpose, so the pipeline pushes the new tags with `az containerapp update`.
6. **Health checks** - polls the API `/api/v1/health` endpoint, purges Front Door and polls the custom domain.

The image tags are runtime parameters with no default: every run names explicit release tags. They reach scripts only through environment variables, never by text substitution into the script.

## Setup

1. Create a deploy service connection (Azure Resource Manager, workload identity federation). Its identity needs Contributor on the ReportMate resource group, AcrPush on the registry, and Storage Blob Data Contributor on the Terraform state container. Allow only the deploy pipeline to use it.
2. Create a separate read-only service connection for the plan pipeline: Reader on the ReportMate resource group and Storage Blob Data Reader on the state container. Never give pull request builds the deploy connection.
3. Create a variable group named `reportmate-secrets` with secret variables `DbPassword`, `ClientPassphrase`, `NextAuthSecret`, `ApiInternalSecret` and `KioskTokens`, and permit only the deploy pipeline to use it. The plan pipeline does not link it and passes placeholder values instead.
4. Create an environment named `reportmate-production` and add required approvers (and, optionally, a branch control check limited to `refs/heads/main`).
5. Create the non-secret var file the pipelines read (`reportmate.prod.tfvars` by default), starting from [`terraform.tfvars.example`](../terraform.tfvars.example). This repository ignores `*.tfvars`, so in your own private repository either un-ignore that one file or keep it in a secure file.
6. Edit the `variables` block in each YAML: service connection names, resource group, registry, container app names, API URL, Front Door names, custom domain and Terraform backend.
7. Create one pipeline per YAML in Azure DevOps. To gate pull requests, add a build-validation branch policy on `main` that runs the plan pipeline; Azure Repos ignores YAML `pr` triggers.

Never enable secrets or the deploy connection for builds of forks. With placeholder secrets, the pull request plan can show Key Vault secrets as changing; review the deploy pipeline's Plan stage for the real diff.

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
