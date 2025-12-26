# ReportMate Database Maintenance - Quick Reference

**Status:** ✅ OPERATIONAL | **Last Updated:** Dec 25, 2024

---

## One-Line Status Check
```powershell
az containerapp job execution list --name reportmate-db-maintenance --resource-group ReportMate --output table
```

## Quick Commands

### Start Manual Execution
```powershell
az containerapp job start --name reportmate-db-maintenance --resource-group ReportMate
```

### View Latest Logs
```powershell
az containerapp job logs show --name reportmate-db-maintenance --resource-group ReportMate --container reportmate-db-maintenance --tail 100
```

### Check Schedule
```powershell
az containerapp job show --name reportmate-db-maintenance --resource-group ReportMate --query "properties.configuration.scheduleTriggerConfig" -o json
```

### Database Stats
```powershell
# Requires psql installed
$env:PGPASSWORD="RmDb7K9mL3qP2wX8vN4zF6H"
psql -h reportmate-database.postgres.database.azure.com -U reportmate -d reportmate -c "
SELECT 
  pg_size_pretty(pg_database_size('reportmate')) as db_size,
  (SELECT COUNT(*) FROM events) as events,
  (SELECT COUNT(*) FROM devices) as devices,
  (SELECT COUNT(*) FROM policy_catalog) as policies;
"
```

---

## Key Information

**Job Name:** `reportmate-db-maintenance`  
**Schedule:** Daily at 2:00 AM UTC (6:00 PM PST)  
**Duration:** ~4 minutes  
**Operations:**
1. Delete events older than 30 days
2. Remove duplicate module records  
3. Clean orphaned module records
4. Remove unreferenced policies
5. Run VACUUM ANALYZE

**First Run Results (Dec 25):**
- Deleted 10,944 old events
- Removed 109 orphaned module records
- Cleaned 47,699 orphaned policies (71% reduction!)

---

## Health Indicators

### Good Signs ✅
- Execution status: "Succeeded"
- Duration: 3-5 minutes
- Database size: 19-21 GB
- Event count: <750K
- Policy count: ~19K

### Warning Signs ⚠️
- Duration: >10 minutes
- Database size: >25 GB
- Event count: >1M
- Execution failures

### Crisis Signs 🚨
- Multiple consecutive failures
- Database size: >30 GB
- Event count: >1.5M
- Duration: >30 minutes

---

## Common Issues

### Job Won't Start
```powershell
# Check job configuration
az containerapp job show --name reportmate-db-maintenance --resource-group ReportMate -o json

# Verify ACR image exists
az acr repository show --name reportmateacr --repository reportmate-maintenance
```

### Can't See Logs
```powershell
# List recent executions
az containerapp job execution list --name reportmate-db-maintenance --resource-group ReportMate

# Get specific execution logs (replace EXECUTION_NAME)
az containerapp job logs show --name reportmate-db-maintenance --resource-group ReportMate --execution EXECUTION_NAME --container reportmate-db-maintenance
```

### Database Connection Failed
```powershell
# Check firewall rules
az postgres flexible-server firewall-rule list --server-name reportmate-database --resource-group ReportMate

# Verify the allow_azure rule exists
az postgres flexible-server firewall-rule show --server-name reportmate-database --resource-group ReportMate --rule-name allow_azure
```

---

## Monitoring Tonight's Run

**Next Scheduled:** Dec 26, 2024, 02:00 UTC

### Check Tomorrow Morning
```powershell
# View execution history
az containerapp job execution list --name reportmate-db-maintenance --resource-group ReportMate --output table

# Check latest logs
az containerapp job logs show --name reportmate-db-maintenance --resource-group ReportMate --container reportmate-db-maintenance --tail 200
```

### Expected Results
- Status: Succeeded
- Duration: 3-5 minutes
- Events deleted: 1,000-5,000 (1 day of growth)
- Duplicates removed: 0-10
- Orphans removed: 0-20
- Policies cleaned: 0-500

---

## Contact & Resources

**Azure Resources:**
- Resource Group: ReportMate
- Region: Canada Central
- Environment: reportmate-env

**Documentation:**
- Full docs: `infrastructure/modules/maintenance/README.md`
- Deployment details: `infrastructure/modules/maintenance/PRODUCTION_REPORT.md`
- Status: `infrastructure/modules/maintenance/DEPLOYMENT_STATUS.md`

**Container:**
- Image: `reportmateacr.azurecr.io/reportmate-maintenance:latest`
- Registry: reportmateacr (Canada Central)
- Size: ~100MB

---

## Quick Wins from First Run

✅ **58,752 records cleaned**
✅ **Policy catalog reduced 71%** (66K → 19K)
✅ **Event retention working** (30-day window)
✅ **Orphan prevention active**

**Bottom line:** Database crisis won't happen again! 🎉
