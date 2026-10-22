# ReportMate Azure Terraform wiki

This module deploys ReportMate's hosted service on Azure. It provisions the PostgreSQL database, the Container Apps that run the API and web dashboard, Front Door, Key Vault, managed identities, monitoring and the database maintenance jobs that keep device records in shape. The API and web application code live in their own repositories; this repository owns the infrastructure they run on.

## Read first

- [Project setup and module usage](../README.md)
- [Input variables](../variables.tf) and [example values](../terraform.tfvars.example)
- [Backend configuration example](../backend.tf.example)
- [Deploy pipeline](../pipelines/README.md)
- [Database schemas and migrations](../schemas/README.md)

## Architecture

The root [main.tf](../main.tf) reads an existing resource group and composes the modules under [modules](../modules). [versions.tf](../versions.tf) pins the `azurerm`, `azuread`, `random` and `null` providers and declares an empty `azurerm` backend, so each deployment supplies its own state location.

Each module owns one part of the service:

- `database` creates the PostgreSQL Flexible Server where the API keeps one JSONB row per device per module.
- `containers` creates the container registry and runs the API and web dashboard on Azure Container Apps.
- `networking` places Azure Front Door in front of the dashboard and API.
- `auth` and `identity` create the Entra ID application registration and the managed identities the containers use.
- `key_vault` holds the database credentials, client passphrases and internal API secrets.
- `storage`, `monitoring` and `functions` supply the storage account, Application Insights and the Function App for scheduled tasks. See the [functions module notes](../modules/functions/README.md).
- `maintenance` runs the database cleanup as a scheduled Container Apps job. See the [maintenance module notes](../modules/maintenance/README.md).

The API image is built by the `reportmate-api` repository and the dashboard image by `reportmate-app-web`. The deploy pipeline mirrors the API image from GitHub Container Registry into the deployment's registry, applies Terraform and rolls both container apps.

Database structure is versioned as numbered SQL files in [schemas](../schemas), with a complete schema for fresh installs and incremental migrations for existing databases.

## Development and verification

Use the current [README](../README.md) for prerequisites and the manual Terraform workflow. Copy `backend.tf.example` and `terraform.tfvars.example` to their working names before planning; both working files are gitignored and must stay out of commits.

Run `terraform fmt -check -recursive` and `terraform validate` before opening a pull request, and review `terraform plan` output against a non-production deployment for any change to a module. The [scripts](../scripts/README.md) `check.ps1` and `status.ps1` report the health of a deployed environment after an apply.

## Guides

- [Container updates](CONTAINER_UPDATE_GUIDE.md)
- [Security practices](SECURITY.md)
- [Database maintenance options](DATABASE_MAINTENANCE_OPTIONS.md)
- [Maintenance quick reference](MAINTENANCE_QUICK_REFERENCE.md)
- [Device archive API](DEVICE_ARCHIVE_API.md)
- [Application utilization on Windows](APPLICATION_UTILIZATION_WINDOWS.md)
- [Application utilization on macOS](APPLICATION_UTILIZATION_MAC_INSTRUCTIONS.md)

## Documentation ownership

Keep this wiki as the entry point and update the linked pages where the facts belong. Examples use fictional data. Deployment inventories, credentials, subscription and tenant identifiers, backend state locations and organization-specific operations belong with their deployment owner, not in this public module.
