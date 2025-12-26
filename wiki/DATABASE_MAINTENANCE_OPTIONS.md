# Database Maintenance Automation Options

## Problem Statement

After policy-level deduplication (80-90% storage reduction), we still need automated maintenance for:
- **Event retention**: Delete events older than 30-90 days
- **Duplicate cleanup**: Remove duplicate module records (1 per device max)
- **Orphaned records**: Delete module records for deleted devices
- **VACUUM**: Reclaim disk space from deleted rows
- **Statistics**: Update query planner statistics

## Option 1: Native PostgreSQL (pg_cron)

**Description**: Use PostgreSQL's built-in `pg_cron` extension for scheduling SQL jobs

**Implementation**:
```sql
-- Enable extension
CREATE EXTENSION pg_cron;

-- Schedule daily cleanup at 2 AM
SELECT cron.schedule('cleanup-old-events', '0 2 * * *', 
  'DELETE FROM events WHERE created_at < NOW() - INTERVAL ''90 days''');

-- Schedule weekly VACUUM at 3 AM Sunday
SELECT cron.schedule('vacuum-tables', '0 3 * * 0', 
  'VACUUM ANALYZE');
```

**Pros**:
- ✅ Native to database - no external dependencies
- ✅ Runs inside database - no API/network calls needed
- ✅ Minimal cost - no additional Azure resources
- ✅ Simple SQL-based maintenance

**Cons**:
- ❌ Azure PostgreSQL Flexible Server may not support pg_cron (need to verify)
- ❌ Limited logging/monitoring compared to external tools
- ❌ No complex logic - just SQL
- ❌ Can't easily run Python/PowerShell scripts

**Cost**: $0 (included in database)

**Best for**: Simple SQL-only maintenance tasks if pg_cron is available

---

## Option 2: Azure Container Apps Jobs (RECOMMENDED)

**Description**: Run containerized Python/PowerShell maintenance script on schedule

**Implementation**:
```yaml
# Container App Job (Terraform)
resource "azurerm_container_app_job" "maintenance" {
  name                = "reportmate-db-maintenance"
  resource_group_name = azurerm_resource_group.rg.name
  location           = azurerm_resource_group.rg.location
  
  template {
    container {
      name   = "maintenance"
      image  = "reportmateacr.azurecr.io/reportmate-maintenance:latest"
      cpu    = 0.25
      memory = "0.5Gi"
    }
  }
  
  schedule_trigger_config {
    cron_expression = "0 2 * * *"  # Daily at 2 AM
  }
}
```

**Pros**:
- ✅ Already using Container Apps - fits existing infrastructure
- ✅ Full Python/PowerShell scripting capability
- ✅ Comprehensive logging via Application Insights
- ✅ Can run complex cleanup logic
- ✅ Easy to update - just push new container image
- ✅ Runs in same VNet as database (secure)

**Cons**:
- ❌ Requires building/maintaining container image
- ❌ Small additional cost (~$2-5/month)
- ❌ More complex setup than pure SQL

**Cost**: ~$2-5/month (minimal compute time)

**Best for**: Production systems needing robust maintenance with logging

---

## Option 3: Azure Functions (Timer Trigger)

**Description**: Serverless Python function runs on schedule

**Implementation**:
```python
# function_app.py
@app.schedule(schedule="0 2 * * *", arg_name="myTimer")
def database_maintenance(myTimer: func.TimerRequest) -> None:
    # Connect to database
    # Run cleanup queries
    # Log results
```

**Pros**:
- ✅ Serverless - no infrastructure management
- ✅ Pay only for execution time
- ✅ Good logging/monitoring via Application Insights
- ✅ Easy to deploy and update

**Cons**:
- ❌ Already using Container Apps API - mixing approaches
- ❌ Cold starts (first run might be slow)
- ❌ 10-minute execution limit (shouldn't be issue)
- ❌ Another service to manage

**Cost**: ~$1-3/month

**Best for**: Simple maintenance if not using Container Apps

---

## Option 4: GitHub Actions (Scheduled Workflow)

**Description**: Run maintenance via GitHub Actions on cron schedule

**Implementation**:
```yaml
# .github/workflows/db-maintenance.yml
name: Database Maintenance
on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM UTC

jobs:
  cleanup:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: python scripts/db-maintenance.py
        env:
          DB_CONNECTION: ${{ secrets.DB_CONNECTION }}
```

**Pros**:
- ✅ Free for public repos, cheap for private
- ✅ Git-tracked maintenance scripts
- ✅ Easy to review/modify via PRs
- ✅ Good logging in GitHub Actions UI

**Cons**:
- ❌ Runs outside Azure (may need firewall rules)
- ❌ Stores database credentials in GitHub Secrets
- ❌ Less secure than Azure-native solutions
- ❌ Can't access VNet-internal database easily

**Cost**: Free (public repos) or ~$0.008/minute (private)

**Best for**: Public projects or when GitHub is primary workflow

---

## Option 5: API Endpoint + External Cron

**Description**: Create `/api/admin/maintenance` endpoint, call from external scheduler

**Implementation**:
```python
# API endpoint
@app.post("/api/admin/maintenance")
async def run_maintenance(auth_key: str):
    if auth_key != MAINTENANCE_KEY:
        raise HTTPException(401)
    # Run cleanup
    return {"cleaned": 1234, "vacuumed": True}
```

**External caller options**:
- Azure Logic Apps (schedule + HTTP call)
- PowerShell script on VM
- Uptime monitoring service webhook
- Your laptop (manual trigger)

**Pros**:
- ✅ Simple endpoint approach
- ✅ Can trigger manually for testing
- ✅ Flexible - any HTTP client can call it
- ✅ Already have API infrastructure

**Cons**:
- ❌ Need external scheduler
- ❌ API must be publicly accessible (with auth)
- ❌ Less robust than dedicated job
- ❌ Maintenance endpoint could timeout on large cleanups

**Cost**: Depends on scheduler used

**Best for**: Quick solution, manual triggers, or ad-hoc maintenance

---

## Recommended Approach: Container Apps Jobs

**Why**:
1. You're already using Container Apps for API
2. Runs in same environment (VNet, logging, monitoring)
3. Can reuse database connection patterns from API
4. Robust logging via Application Insights
5. Easy to update maintenance logic (push new image)

**Implementation Plan**:

### 1. Create maintenance script
```python
# modules/maintenance/maintenance.py
import psycopg2
import os
from datetime import datetime, timedelta

def cleanup_old_events(cursor, retention_days=30):
    """Delete events older than retention period"""
    cutoff = datetime.now() - timedelta(days=retention_days)
    cursor.execute("DELETE FROM events WHERE created_at < %s", (cutoff,))
    return cursor.rowcount

def remove_duplicates(cursor):
    """Keep only newest module record per device"""
    # Implementation here
    pass

def remove_orphans(cursor):
    """Delete module records for deleted devices"""
    # Implementation here
    pass

def vacuum_database(cursor):
    """Run VACUUM ANALYZE"""
    cursor.execute("VACUUM ANALYZE")

if __name__ == "__main__":
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    cursor = conn.cursor()
    
    print("Starting maintenance...")
    cleaned = cleanup_old_events(cursor, 30)
    print(f"  Deleted {cleaned} old events")
    
    # More cleanup...
    
    conn.commit()
    conn.close()
```

### 2. Create Dockerfile
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY maintenance.py .
CMD ["python", "maintenance.py"]
```

### 3. Add to Terraform
```hcl
resource "azurerm_container_app_job" "maintenance" {
  name                         = "reportmate-db-maintenance"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.rg.name
  location                     = azurerm_resource_group.rg.location
  
  template {
    container {
      name   = "maintenance"
      image  = "${azurerm_container_registry.acr.login_server}/reportmate-maintenance:latest"
      cpu    = 0.25
      memory = "0.5Gi"
      
      env {
        name  = "DATABASE_URL"
        value = "postgresql://..."
      }
    }
  }
  
  schedule_trigger_config {
    cron_expression          = "0 2 * * *"  # Daily at 2 AM
    parallelism              = 1
    replica_completion_count = 1
  }
}
```

### 4. Deploy workflow
```bash
# Build and push maintenance container
cd infrastructure/modules/maintenance
docker build -t reportmateacr.azurecr.io/reportmate-maintenance:latest .
docker push reportmateacr.azurecr.io/reportmate-maintenance:latest

# Update infrastructure
cd ../..
terraform apply
```

### 5. Manual trigger for testing
```bash
az containerapp job start \
  --name reportmate-db-maintenance \
  --resource-group ReportMate
```

## Summary Comparison

| Feature | pg_cron | Container Jobs | Functions | GitHub | API Endpoint |
|---------|---------|----------------|-----------|--------|--------------|
| **Cost** | $0 | ~$3/mo | ~$2/mo | Free-$8 | Varies |
| **Setup Complexity** | Low | Medium | Medium | Low | Low |
| **Logging** | Basic | Excellent | Good | Good | Basic |
| **Flexibility** | SQL only | Full scripts | Python | Any | HTTP |
| **Security** | Best | Good | Good | Lower | Medium |
| **Maintenance** | None | Low | Low | None | Medium |
| **Fits Architecture** | N/A | ✅ Yes | Partial | No | ✅ Yes |

## Recommendation

Start with **Container Apps Jobs** because:
1. Matches your existing Container Apps architecture
2. Production-ready logging and monitoring
3. Easy to test and iterate
4. Can handle complex cleanup logic
5. Scales with your infrastructure

Keep it simple initially:
- Daily at 2 AM UTC
- 30-day event retention
- Duplicate/orphan cleanup
- Weekly VACUUM

Monitor for 2-4 weeks, then adjust retention periods based on growth.
