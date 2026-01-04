# Azure Functions Deployment Guide

Complete guide for deploying ReportMate Azure Functions through Terraform and Azure DevOps pipeline.

## Prerequisites

1. **Azure CLI** installed and authenticated
   ```bash
   az login
   az account set --subscription "ReportMate"
   ```

2. **Terraform** installed (v1.0+)
   ```bash
   terraform version
   ```

3. **Azure Functions Core Tools** installed
   ```bash
   func --version
   ```

4. **Python 3.11** installed
   ```bash
   python --version
   ```

## Quick Start

### 1. Deploy Infrastructure

```bash
# Navigate to infrastructure directory
cd infrastructure/azure

# Initialize Terraform
terraform init

# Review planned changes
terraform plan

# Deploy Functions infrastructure
terraform apply -auto-approve
```

**Resources Created**:
- Storage Account: `reportmatefuncXXXX`
- App Service Plan: `reportmate-functions-plan` (Consumption Y1)
- Functions App: `reportmate-functions`

### 2. Deploy Function Code

```bash
# Navigate to functions directory
cd ../../functions

# Install dependencies locally (for testing)
pip install -r requirements.txt

# Deploy to Azure
func azure functionapp publish reportmate-functions --python
```

### 3. Verify Deployment

```bash
# Check Functions App status
az functionapp show \
  --name reportmate-functions \
  --resource-group ReportMate \
  --query "{name:name, state:state, defaultHostName:defaultHostName}"

# List functions
az functionapp function list \
  --name reportmate-functions \
  --resource-group ReportMate \
  --query "[].{name:name, status:config.disabled}" \
  --output table

# View recent logs
az functionapp logs tail \
  --name reportmate-functions \
  --resource-group ReportMate
```

## Environment Variables

The Functions App is automatically configured with these environment variables:

| Variable | Source | Purpose |
|----------|--------|---------|
| `REPORTMATE_API_URL` | Terraform (from containers module) | API base URL |
| `REPORTMATE_PASSPHRASE` | Terraform variable `client_passphrases` | API authentication |
| `TEAMS_WEBHOOK_URL` | Terraform variable (optional) | Teams alerts |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | Terraform (from monitoring module) | Telemetry |
| `FUNCTIONS_WORKER_RUNTIME` | Hardcoded: `python` | Runtime configuration |

### Setting Teams Webhook URL

**Option 1: Terraform Variable** (Recommended for CI/CD)

```bash
# Set via environment variable before terraform apply
export TF_VAR_teams_webhook_url="https://outlook.office.com/webhook/..."
terraform apply
```

**Option 2: Azure Portal**

1. Navigate to Functions App → Configuration → Application settings
2. Click "+ New application setting"
3. Name: `TEAMS_WEBHOOK_URL`
4. Value: `https://outlook.office.com/webhook/...`
5. Click OK → Save

**Option 3: Azure CLI**

```bash
az functionapp config appsettings set \
  --name reportmate-functions \
  --resource-group ReportMate \
  --settings TEAMS_WEBHOOK_URL="https://outlook.office.com/webhook/..."
```

## Pipeline Integration

### Adding to Azure DevOps Pipeline

Edit `pipelines/reportmate-deploy-infra.yml`:

```yaml
stages:
  # ... existing stages ...

  - stage: DeployFunctions
    displayName: 'Deploy Azure Functions'
    dependsOn: 
      - DeployInfrastructure
    jobs:
      - job: BuildAndDeployFunctions
        displayName: 'Build and Deploy Functions Code'
        pool:
          vmImage: 'ubuntu-latest'
        steps:
          - task: UsePythonVersion@0
            inputs:
              versionSpec: '3.11'
              addToPath: true
            displayName: 'Use Python 3.11'

          - script: |
              pip install --upgrade pip
              pip install -r functions/requirements.txt
            displayName: 'Install dependencies'

          - task: AzureFunctionApp@1
            inputs:
              azureSubscription: 'ReportMate-ServiceConnection'
              appType: 'functionAppLinux'
              appName: 'reportmate-functions'
              package: 'functions'
              runtimeStack: 'PYTHON|3.11'
              deploymentMethod: 'zipDeploy'
            displayName: 'Deploy Functions to Azure'
```

## Testing Functions

### Test Locally

```bash
cd functions

# Install dependencies
pip install -r requirements.txt

# Start Functions runtime locally
func start --python

# In another terminal, test storage alerts
python test_storage_quick.py
```

### Test in Azure

```bash
# Trigger function manually (will run on timer schedule automatically)
func azure functionapp invoke reportmate_storage_alerts \
  --name reportmate-functions

# Check execution result
az monitor app-insights query \
  --app reportmate-app-insights \
  --analytics-query "requests | where cloud_RoleName == 'reportmate-functions' | order by timestamp desc | take 1"
```

## Function Schedule

Storage alerts function runs daily at **7:00 AM PST** (15:00 UTC):

```
CRON Schedule: 0 0 15 * * *
```

To change schedule:

1. **Edit function code** (`functions/function_app.py`):
   ```python
   @app.schedule(schedule="0 0 9 * * *", ...)  # 9:00 AM UTC
   ```

2. **Redeploy**:
   ```bash
   func azure functionapp publish reportmate-functions --python
   ```

## Monitoring

### View Logs in Real-Time

```bash
az functionapp logs tail \
  --name reportmate-functions \
  --resource-group ReportMate \
  --follow
```

### Query Application Insights

```bash
# View all storage alert executions
az monitor app-insights query \
  --app reportmate-app-insights \
  --analytics-query "
    traces 
    | where cloud_RoleName == 'reportmate-functions'
    | where message contains 'storage'
    | order by timestamp desc
    | take 20
  "

# Check for errors
az monitor app-insights query \
  --app reportmate-app-insights \
  --analytics-query "
    exceptions
    | where cloud_RoleName == 'reportmate-functions'
    | order by timestamp desc
    | take 10
  "
```

### View in Azure Portal

1. Navigate to **Azure Portal** → **Function App** (`reportmate-functions`)
2. Click **Monitor** → **Logs**
3. Run Kusto queries:
   ```kusto
   traces
   | where message contains "Storage alert"
   | order by timestamp desc
   ```

## Troubleshooting

### Function Not Executing

**Check timer status:**
```bash
az functionapp function show \
  --name reportmate-functions \
  --resource-group ReportMate \
  --function-name reportmate_storage_alerts \
  --query "config"
```

**Verify environment variables:**
```bash
az functionapp config appsettings list \
  --name reportmate-functions \
  --resource-group ReportMate \
  --query "[?name=='REPORTMATE_API_URL' || name=='REPORTMATE_PASSPHRASE'].{name:name, value:value}"
```

### API Authentication Errors

**Test API connection:**
```bash
cd functions
python test_storage_single.py 0F33V9G25083HJ
```

**Check passphrase:**
```bash
# Should match value in Terraform variables
az functionapp config appsettings list \
  --name reportmate-functions \
  --resource-group ReportMate \
  --query "[?name=='REPORTMATE_PASSPHRASE'].value" -o tsv
```

### Deployment Failures

**Check deployment logs:**
```bash
az functionapp deployment list \
  --name reportmate-functions \
  --resource-group ReportMate

# Get latest deployment details
az functionapp deployment show \
  --name reportmate-functions \
  --resource-group ReportMate \
  --deployment-id <id-from-list>
```

**View deployment center logs:**
1. Azure Portal → Functions App → Deployment Center
2. Click on latest deployment
3. View detailed logs

## Cost Management

### Consumption Plan Costs

- **Execution**: First 1 million executions free
- **Compute Time**: First 400,000 GB-s free
- **Storage**: ~$0.50-2/month for function storage

**Estimated Monthly Cost**: $5-10 (well within free tier for storage alerts)

### Monitor Usage

```bash
# Check function executions
az monitor app-insights query \
  --app reportmate-app-insights \
  --analytics-query "
    requests
    | where cloud_RoleName == 'reportmate-functions'
    | summarize 
        executions=count(),
        avg_duration=avg(duration)
      by bin(timestamp, 1d)
    | order by timestamp desc
  "
```

## Security Best Practices

1. **Use Managed Identity**: Functions App has system-assigned identity for Azure resource access
2. **Secure Secrets**: Store sensitive values (webhook URLs, passphrases) in Key Vault
3. **HTTPS Only**: All traffic forced to HTTPS (configured in Terraform)
4. **Network Restrictions**: Consider adding IP restrictions if needed
5. **Audit Logs**: Enable diagnostic settings for audit trail

## Adding New Functions

### 1. Create Function Code

Edit `functions/function_app.py`:

```python
@app.schedule(
    schedule="0 0 12 * * *",  # Daily at noon UTC
    arg_name="timer",
    run_on_startup=False,
    use_monitor=True
)
def my_new_alert_function(timer: func.TimerRequest) -> None:
    """My new scheduled function"""
    if timer.past_due:
        logging.info('Timer trigger is past due!')
    
    logging.info('My function executed at %s', datetime.utcnow())
    
    # Your logic here
```

### 2. Add Dependencies

Add to `functions/requirements.txt` if needed:
```
requests>=2.31.0
your-new-package>=1.0.0
```

### 3. Deploy

```bash
cd functions
func azure functionapp publish reportmate-functions --python
```

## Resources

- **Function Code**: `/functions/`
- **Infrastructure**: `/infrastructure/azure/modules/functions/`
- **Pipeline**: `/pipelines/reportmate-deploy-infra.yml`
- **Documentation**: `/functions/reportmate-storage-alerts/README.md`

## Support

For issues or questions:
1. Check logs: `az functionapp logs tail --name reportmate-functions --resource-group ReportMate`
2. Review test results: `/functions/STORAGE_ALERTS_TEST_RESULTS.md`
3. Test locally: `cd functions && func start --python`
