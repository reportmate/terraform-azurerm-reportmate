# Check Status - ReportMate
# Quick health check of all infrastructure components

param(
    [string]$ResourceGroup = "ReportMate"
)

Write-Host "🔍 Checking ReportMate Infrastructure Status..." -ForegroundColor Green

# Check Azure Functions
Write-Host "`n⚡ Azure Functions Status:" -ForegroundColor Yellow
try {
    $functionsStatus = az functionapp show --name reportmate-api --resource-group $ResourceGroup --query "state" --output tsv
    Write-Host "   reportmate-api: $functionsStatus" -ForegroundColor $(if ($functionsStatus -eq "Running") { "Green" } else { "Red" })
    
    # Test API endpoints
    try {
        $healthResponse = Invoke-RestMethod -Uri "https://reportmate-api.azurewebsites.net/api/health" -TimeoutSec 10
        Write-Host "   /api/health: ✅ OK" -ForegroundColor Green
        
        $devicesResponse = Invoke-RestMethod -Uri "https://reportmate-api.azurewebsites.net/api/devices" -TimeoutSec 10
        $deviceCount = ($devicesResponse | Measure-Object).Count
        Write-Host "   /api/devices: ✅ OK ($deviceCount devices)" -ForegroundColor Green
    } catch {
        Write-Host "   API endpoints: ❌ Failed" -ForegroundColor Red
    }
} catch {
    Write-Host "   reportmate-api: ❌ Not found" -ForegroundColor Red
}

# Check Database
Write-Host "`n🗄️  Database Status:" -ForegroundColor Yellow
try {
    $dbStatus = az postgres flexible-server show --name reportmate-database --resource-group $ResourceGroup --query "state" --output tsv
    Write-Host "   reportmate-database: $dbStatus" -ForegroundColor $(if ($dbStatus -eq "Ready") { "Green" } else { "Red" })
    
    # Test database connection
    try {
        $deviceCount = az postgres flexible-server execute --name reportmate-database --admin-user reportmate --admin-password "2sSWbVxyqjXp9WUpeMmzRaC" --database-name reportmate --querytext "SELECT COUNT(*) as count FROM devices;" --output json | ConvertFrom-Json
        Write-Host "   Connection: ✅ OK ($($deviceCount[0].count) devices)" -ForegroundColor Green
    } catch {
        Write-Host "   Connection: ❌ Failed" -ForegroundColor Red
    }
} catch {
    Write-Host "   reportmate-database: ❌ Not found" -ForegroundColor Red
}

# Check Container Apps (if they exist)
Write-Host "`n🐳 Container Apps Status:" -ForegroundColor Yellow
try {
    $containerApps = az containerapp list --resource-group $ResourceGroup --query "[].{name:name,status:properties.provisioningState}" --output json | ConvertFrom-Json
    
    if ($containerApps.Count -gt 0) {
        foreach ($app in $containerApps) {
            $statusColor = if ($app.status -eq "Succeeded") { "Green" } else { "Red" }
            Write-Host "   $($app.name): $($app.status)" -ForegroundColor $statusColor
        }
    } else {
        Write-Host "   No container apps found" -ForegroundColor Cyan
    }
} catch {
    Write-Host "   Container apps: ❌ Error checking" -ForegroundColor Red
}

# Check Storage Account
Write-Host "`n💾 Storage Status:" -ForegroundColor Yellow
try {
    $storageAccounts = az storage account list --resource-group $ResourceGroup --query "[].{name:name,status:primaryEndpoints.blob}" --output json | ConvertFrom-Json
    
    foreach ($storage in $storageAccounts) {
        $statusColor = if ($storage.status) { "Green" } else { "Red" }
        $status = if ($storage.status) { "✅ OK" } else { "❌ Failed" }
        Write-Host "   $($storage.name): $status" -ForegroundColor $statusColor
    }
} catch {
    Write-Host "   Storage accounts: ❌ Error checking" -ForegroundColor Red
}

# Summary
Write-Host "`n📊 Quick Summary:" -ForegroundColor Cyan
Write-Host "   🔗 API Health: https://reportmate-api.azurewebsites.net/api/health" -ForegroundColor Cyan
Write-Host "   🔍 API Debug: https://reportmate-api.azurewebsites.net/api/debug" -ForegroundColor Cyan
Write-Host "   📱 Dashboard: https://reportmate-frontend.azurewebsites.net" -ForegroundColor Cyan

Write-Host "`n✅ Status check completed!" -ForegroundColor Green
