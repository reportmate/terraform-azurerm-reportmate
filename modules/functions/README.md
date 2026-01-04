# Azure Functions Module

This Terraform module creates an Azure Functions App for running scheduled tasks and serverless functions in the ReportMate infrastructure.

## Features

- **Azure Functions App**: Linux-based consumption plan for cost-effective serverless execution
- **Storage Account**: Dedicated storage for function code and state
- **App Service Plan**: Consumption (Y1) SKU for automatic scaling
- **Application Insights Integration**: Built-in monitoring and logging
- **Managed Identity**: System-assigned identity for secure Azure resource access
- **Environment Variables**: Pre-configured with ReportMate API authentication

## Resources Created

1. **Storage Account** (`azurerm_storage_account.functions`)
   - Used for Functions App internal storage
   - Standard_LRS replication
   - Secure HTTPS-only access
   - Minimum TLS 1.2

2. **App Service Plan** (`azurerm_service_plan.functions`)
   - Consumption-based (Y1 SKU)
   - Linux OS
   - Automatic scaling based on demand

3. **Linux Function App** (`azurerm_linux_function_app.functions`)
   - Python 3.11 runtime
   - Always-on disabled (Consumption plan)
   - System-assigned managed identity
   - Application Insights integration
   - Environment variables for API access

## Usage

```hcl
module "functions" {
  source = "./modules/functions"

  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location

  function_app_name = "reportmate-functions"
  sku_name          = "Y1"

  # API Configuration
  api_base_url       = "https://reportmate-api.azurewebsites.net"
  client_passphrases = var.client_passphrases
  teams_webhook_url  = var.teams_webhook_url

  # Monitoring
  app_insights_connection_string = module.monitoring.app_insights_connection_string

  # Optional Key Vault access
  key_vault_id = module.key_vault.key_vault_id

  tags = var.tags
}
```

## Current Functions

### Storage Alerts Function (`reportmate_storage_alerts`)

**Schedule**: Daily at 7:00 AM PST (15:00 UTC)  
**Trigger**: Timer (CRON: `0 0 15 * * *`)  
**Purpose**: Monitor device storage and alert on low disk space

**Logic**:
1. Fetches all devices from ReportMate API
2. For each device, retrieves hardware/storage data
3. Filters internal drives (capacity > 10GB)
4. Alerts if any drive has < 10% free space
5. Sends formatted alert to Microsoft Teams webhook

**Environment Variables Required**:
- `REPORTMATE_API_URL`: Base URL for ReportMate API
- `REPORTMATE_PASSPHRASE`: API authentication passphrase
- `TEAMS_WEBHOOK_URL`: Microsoft Teams incoming webhook URL

## Deployment

### 1. Deploy Infrastructure (Terraform)

```bash
cd infrastructure/azure
terraform init
terraform plan
terraform apply
```

This creates the Functions App and storage account.

### 2. Deploy Function Code

```bash
cd functions
func azure functionapp publish reportmate-functions --python
```

Or use ZIP deployment:

```bash
cd functions
func azure functionapp deployment source config-zip \
  --resource-group ReportMate \
  --name reportmate-functions \
  --src function-app.zip
```

### 3. Verify Deployment

```bash
# Check Functions App status
az functionapp show \
  --name reportmate-functions \
  --resource-group ReportMate \
  --query "state"

# View function logs
az functionapp logs tail \
  --name reportmate-functions \
  --resource-group ReportMate
```

## Variables

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
| `resource_group_name` | Resource group name | `string` | - | yes |
| `location` | Azure region | `string` | - | yes |
| `function_app_name` | Functions App name | `string` | `"reportmate-functions"` | no |
| `sku_name` | App Service Plan SKU | `string` | `"Y1"` | no |
| `api_base_url` | ReportMate API URL | `string` | - | yes |
| `client_passphrases` | API passphrase | `string` | - | yes |
| `teams_webhook_url` | Teams webhook URL | `string` | `""` | no |
| `app_insights_connection_string` | App Insights connection | `string` | - | yes |
| `key_vault_id` | Key Vault resource ID | `string` | `null` | no |
| `tags` | Resource tags | `map(string)` | `{}` | no |

## Outputs

| Name | Description |
|------|-------------|
| `function_app_id` | Functions App resource ID |
| `function_app_name` | Functions App name |
| `function_app_default_hostname` | Default hostname |
| `function_app_identity_principal_id` | Managed identity principal ID |
| `storage_account_name` | Storage account name |

## Monitoring

Functions are automatically monitored through Application Insights:

1. **View in Azure Portal**:
   - Navigate to Functions App → Monitor → Logs
   - View execution history, duration, and success/failure

2. **Query with Kusto**:
   ```kusto
   traces
   | where cloud_RoleName == "reportmate-functions"
   | where timestamp > ago(1h)
   | order by timestamp desc
   ```

3. **Check Function Executions**:
   ```kusto
   requests
   | where cloud_RoleName == "reportmate-functions"
   | where name contains "reportmate_storage_alerts"
   | summarize count(), avg(duration) by bin(timestamp, 1h)
   ```

## Security

1. **Managed Identity**: System-assigned identity for Azure resource access
2. **HTTPS Only**: All traffic forced to HTTPS
3. **TLS 1.2+**: Minimum TLS version enforced
4. **Environment Variables**: Sensitive values stored securely in Function App configuration
5. **Optional Key Vault**: Can integrate with Key Vault for secret management

## Cost Optimization

- **Consumption Plan (Y1)**: Pay only for execution time
- **Free Grant**: 1 million requests and 400,000 GB-s per month included
- **Storage**: Minimal cost for function code storage (~$1/month)
- **Application Insights**: Included in Function App cost

**Estimated Monthly Cost**: ~$5-10 for moderate usage

## Troubleshooting

### Function Not Triggering

```bash
# Check timer trigger status
az functionapp function show \
  --name reportmate-functions \
  --resource-group ReportMate \
  --function-name reportmate_storage_alerts
```

### View Execution History

```bash
# Recent invocations
az monitor app-insights query \
  --app reportmate-app-insights \
  --analytics-query "requests | where cloud_RoleName == 'reportmate-functions' | order by timestamp desc | take 10"
```

### Test Function Manually

```bash
# Trigger function via HTTP (if HTTP trigger enabled)
curl -X POST https://reportmate-functions.azurewebsites.net/api/reportmate_storage_alerts?code=<function-key>
```

## Adding New Functions

1. **Create function file**: `/functions/function_app.py`
   ```python
   @app.schedule(schedule="0 0 * * * *", arg_name="timer", run_on_startup=False)
   def my_new_function(timer: func.TimerRequest) -> None:
       logging.info('My new function triggered')
   ```

2. **Deploy updated code**:
   ```bash
   cd functions
   func azure functionapp publish reportmate-functions --python
   ```

3. **Monitor execution**:
   ```bash
   az functionapp logs tail --name reportmate-functions --resource-group ReportMate
   ```

## References

- [Azure Functions Python Developer Guide](https://learn.microsoft.com/en-us/azure/azure-functions/functions-reference-python)
- [Azure Functions Timer Trigger](https://learn.microsoft.com/en-us/azure/azure-functions/functions-bindings-timer)
- [Azure Functions Consumption Plan](https://learn.microsoft.com/en-us/azure/azure-functions/consumption-plan)
