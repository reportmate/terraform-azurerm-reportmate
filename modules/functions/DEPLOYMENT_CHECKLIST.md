# Azure Functions Deployment Checklist

Quick reference checklist for deploying ReportMate Azure Functions.

## Pre-Deployment Checklist

- [ ] Azure CLI authenticated (`az login`)
- [ ] Terraform installed and initialized
- [ ] Azure Functions Core Tools installed (`func --version`)
- [ ] Python 3.11 installed
- [ ] Teams webhook URL obtained (optional)
- [ ] Verified `terraform.tfvars` values are correct

## Infrastructure Deployment

- [ ] Navigate to `infrastructure/azure`
- [ ] Run `terraform init` (if first time)
- [ ] Run `terraform plan` and review changes
- [ ] Run `terraform apply -auto-approve`
- [ ] Verify Functions App created:
  ```bash
  az functionapp show --name reportmate-functions --resource-group ReportMate
  ```

## Function Code Deployment

- [ ] Navigate to `functions/` directory
- [ ] Install dependencies locally for testing:
  ```bash
  pip install -r requirements.txt
  ```
- [ ] Test function locally (optional):
  ```bash
  func start --python
  python test_storage_quick.py
  ```
- [ ] Deploy to Azure:
  ```bash
  func azure functionapp publish reportmate-functions --python
  ```
- [ ] Verify deployment:
  ```bash
  az functionapp function list --name reportmate-functions --resource-group ReportMate
  ```

## Configuration

- [ ] Set Teams webhook URL (if using alerts):
  ```bash
  az functionapp config appsettings set \
    --name reportmate-functions \
    --resource-group ReportMate \
    --settings TEAMS_WEBHOOK_URL="your-webhook-url"
  ```
- [ ] Verify environment variables:
  ```bash
  az functionapp config appsettings list \
    --name reportmate-functions \
    --resource-group ReportMate
  ```

## Verification

- [ ] Check function status:
  ```bash
  az functionapp show --name reportmate-functions --resource-group ReportMate --query "state"
  ```
- [ ] View function list:
  ```bash
  az functionapp function list --name reportmate-functions --resource-group ReportMate
  ```
- [ ] Test manual trigger (optional):
  ```bash
  func azure functionapp invoke reportmate_storage_alerts --name reportmate-functions
  ```
- [ ] View logs:
  ```bash
  az functionapp logs tail --name reportmate-functions --resource-group ReportMate
  ```

## Monitoring Setup

- [ ] Navigate to Azure Portal → Functions App
- [ ] Check Application Insights is connected
- [ ] Run test query in Logs:
  ```kusto
  traces
  | where cloud_RoleName == "reportmate-functions"
  | order by timestamp desc
  | take 10
  ```
- [ ] Set up alerts (optional):
  - Function failures
  - Execution duration > threshold
  - Low storage alerts not sent

## Schedule Verification

- [ ] Verify schedule is correct (7:00 AM PST = 15:00 UTC):
  ```bash
  az functionapp function show \
    --name reportmate-functions \
    --resource-group ReportMate \
    --function-name reportmate_storage_alerts \
    --query "config.schedule"
  ```
- [ ] Expected output: `"0 0 15 * * *"`

## Security Checklist

- [ ] HTTPS Only enabled (auto-configured by Terraform)
- [ ] TLS 1.2+ enforced (auto-configured by Terraform)
- [ ] Managed identity created
- [ ] Client passphrase configured
- [ ] Sensitive variables marked sensitive in Terraform
- [ ] Key Vault integration (optional, if enabled)

## Post-Deployment

- [ ] Wait for first scheduled run (7:00 AM PST) or trigger manually
- [ ] Check execution logs for success
- [ ] Verify Teams notification received (if webhook configured)
- [ ] Test alert with device having low storage (if possible)
- [ ] Document any issues or observations

## Troubleshooting Reference

If issues occur, check:

1. **Function not executing**: View timer status and logs
2. **API authentication errors**: Verify passphrase matches
3. **Teams notifications not sent**: Check webhook URL
4. **Deployment failures**: Review deployment center logs
5. **Module import errors**: Verify dependencies in requirements.txt

**Quick troubleshooting commands**:
```bash
# View recent executions
az monitor app-insights query \
  --app reportmate-app-insights \
  --analytics-query "requests | where cloud_RoleName == 'reportmate-functions' | order by timestamp desc | take 10"

# Check for errors
az monitor app-insights query \
  --app reportmate-app-insights \
  --analytics-query "exceptions | where cloud_RoleName == 'reportmate-functions' | order by timestamp desc | take 10"
```

## Rollback Plan

If deployment fails:

1. **Infrastructure issues**:
   ```bash
   cd infrastructure/azure
   terraform destroy -target=module.functions
   ```

2. **Function code issues**:
   - Redeploy previous working version
   - Check deployment history in Azure Portal
   - Restore from source control

3. **Complete rollback**:
   - Remove Functions module from `main.tf`
   - Run `terraform apply` to remove infrastructure
   - Restore previous git commit

## Success Criteria

✅ Functions App running and healthy  
✅ Storage alerts function listed and enabled  
✅ Schedule configured correctly (7:00 AM PST)  
✅ Environment variables set properly  
✅ Application Insights connected  
✅ First execution successful  
✅ Teams notification sent (if configured)  
✅ No errors in logs

## Next Steps After Deployment

1. Monitor first few scheduled executions
2. Review alert accuracy (false positives/negatives)
3. Adjust storage threshold if needed (currently 10%)
4. Add additional scheduled functions as needed
5. Integrate with Azure DevOps pipeline (optional)

## Documentation References

- **Module README**: `/infrastructure/azure/modules/functions/README.md`
- **Deployment Guide**: `/infrastructure/azure/modules/functions/DEPLOYMENT.md`
- **Implementation Summary**: `/infrastructure/azure/modules/functions/IMPLEMENTATION_COMPLETE.md`
- **Test Results**: `/functions/STORAGE_ALERTS_TEST_RESULTS.md`
- **Function Documentation**: `/functions/reportmate-storage-alerts/README.md`

---

**Deployment Date**: _______________  
**Deployed By**: _______________  
**Verified By**: _______________  
**Issues**: _______________
