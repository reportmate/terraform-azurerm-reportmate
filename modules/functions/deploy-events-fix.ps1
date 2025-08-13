# Deploy Events API Fix to Azure Functions
# This script packages and deploys the fixed events endpoint

Write-Host "🔧 Deploying Events API Fix to Azure Functions" -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan

# Set working directory to functions folder
Set-Location $PSScriptRoot

# Create deployment package
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$packageName = "events-api-fix-$timestamp.zip"

Write-Host "📦 Creating deployment package: $packageName" -ForegroundColor Yellow

# Clean up any existing package files
Remove-Item -Path "*.zip" -Force -ErrorAction SilentlyContinue

# Create the deployment package
$filesToInclude = @(
    "api/events/__init__.py",
    "api/events/function.json",
    "api/devices/__init__.py", 
    "api/devices/function.json",
    "shared/database.py",
    "shared/utils.py",
    "host.json",
    "requirements.txt"
)

# Create temporary directory for packaging
$tempDir = "temp_deployment_$timestamp"
New-Item -ItemType Directory -Path $tempDir -Force | Out-Null

try {
    # Copy files to temp directory maintaining structure
    foreach ($file in $filesToInclude) {
        $sourcePath = $file
        $destPath = Join-Path $tempDir $file
        
        # Create directory structure if needed
        $destDir = Split-Path $destPath -Parent
        if (-not (Test-Path $destDir)) {
            New-Item -ItemType Directory -Path $destDir -Force | Out-Null
        }
        
        if (Test-Path $sourcePath) {
            Copy-Item $sourcePath $destPath -Force
            Write-Host "  ✅ Added: $file" -ForegroundColor Green
        } else {
            Write-Warning "  ⚠️  Missing: $file"
        }
    }
    
    # Create the zip package
    Compress-Archive -Path "$tempDir/*" -DestinationPath $packageName -CompressionLevel Optimal -Force
    Write-Host "✅ Package created: $packageName" -ForegroundColor Green
    
} finally {
    # Clean up temp directory
    Remove-Item -Path $tempDir -Recurse -Force -ErrorAction SilentlyContinue
}

# Deploy to Azure Functions
Write-Host "🚀 Deploying to Azure Functions..." -ForegroundColor Yellow

# Get the function app name
$functionApps = az functionapp list --query "[?contains(name, 'reportmate')].name" -o tsv

if ($functionApps) {
    $functionAppName = $functionApps | Select-Object -First 1
    Write-Host "📍 Found Function App: $functionAppName" -ForegroundColor Green
    
    try {
        # Deploy the package
        Write-Host "🔄 Uploading package..." -ForegroundColor Yellow
        az functionapp deployment source config-zip --resource-group "ReportMate" --name $functionAppName --src $packageName
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Deployment successful!" -ForegroundColor Green
            
            # Test the endpoints
            Write-Host "🧪 Testing endpoints..." -ForegroundColor Yellow
            
            Start-Sleep -Seconds 30  # Wait for deployment to settle
            
            try {
                Write-Host "Testing /api/events endpoint..."
                $eventsResponse = Invoke-RestMethod -Uri "https://$functionAppName.azurewebsites.net/api/events" -Method Get -TimeoutSec 30
                Write-Host "✅ Events endpoint: OK" -ForegroundColor Green
                Write-Host "Events count: $($eventsResponse.count)" -ForegroundColor White
            } catch {
                Write-Warning "⚠️  Events endpoint test failed: $($_.Exception.Message)"
            }
            
            try {
                Write-Host "Testing /api/devices endpoint..."
                $devicesResponse = Invoke-RestMethod -Uri "https://$functionAppName.azurewebsites.net/api/devices" -Method Get -TimeoutSec 30
                Write-Host "✅ Devices endpoint: OK" -ForegroundColor Green
                Write-Host "Devices count: $($devicesResponse.Count)" -ForegroundColor White
            } catch {
                Write-Warning "⚠️  Devices endpoint test failed: $($_.Exception.Message)"
            }
            
        } else {
            Write-Error "❌ Deployment failed with exit code: $LASTEXITCODE"
            exit 1
        }
        
    } catch {
        Write-Error "❌ Deployment error: $($_.Exception.Message)"
        exit 1
    }
    
} else {
    Write-Error "❌ No ReportMate function app found"
    exit 1
}

Write-Host ""
Write-Host "🎉 Events API Fix Deployment Complete!" -ForegroundColor Green
Write-Host "=======================================" -ForegroundColor Green
Write-Host "Package: $packageName" -ForegroundColor White
Write-Host "Function App: $functionAppName" -ForegroundColor White
Write-Host "Status: Deployed and tested" -ForegroundColor White

# Clean up deployment package
Remove-Item -Path $packageName -Force -ErrorAction SilentlyContinue
Write-Host "🧹 Cleaned up deployment package" -ForegroundColor Gray
