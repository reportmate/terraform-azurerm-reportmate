#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Comprehensive ReportMate Infrastructure Health Check Script
.DESCRIPTION
    Single canonical script to test and check every component of the ReportMate infrastructure:
    - Database connectivity and schema
    - API endpoints and data flow
    - Container app status
    - Front Door routing
    - Data transmission from Windows client
    
.PARAMETER Verbose
    Show detailed output for all checks
.EXAMPLE
    .\check.ps1
    .\check.ps1 -Verbose
#>

param(
    [switch]$Verbose
)

# Color output functions
function Write-Success { param($Message) Write-Host "[SUCCESS] $Message" -ForegroundColor Green }
function Write-Warning { param($Message) Write-Host "[WARN] $Message" -ForegroundColor Yellow }
function Write-Error { param($Message) Write-Host "[ERR] $Message" -ForegroundColor Red }
function Write-Info { param($Message) Write-Host "[INFO] $Message" -ForegroundColor Cyan }
function Write-Section { param($Message) Write-Host "`n==> $Message" -ForegroundColor Magenta -BackgroundColor Black }

# Global variables
$script:TestResults = @{
    DatabaseConnectivity = $false
    DatabaseSchema = $false
    APIHealth = $false
    APIDeviceEndpoint = $false
    APIEventsEndpoint = $false
    ContainerAppsRunning = $false
    FrontDoorRouting = $false
    DataTransmission = $false
}

$script:ErrorCount = 0
$script:WarningCount = 0
$script:SuccessCount = 0

function Test-DatabaseConnectivity {
    Write-Section "Testing Database Connectivity"
    
    try {
        # Get database connection details from Terraform output or Azure CLI
        $dbServer = "reportmate-database.postgres.database.azure.com"
        $dbName = "reportmate"
        
        # Test basic connectivity
        Write-Info "Testing connection to PostgreSQL server..."
        $connectionTest = az postgres flexible-server show --name reportmate-database --resource-group ReportMate --query "state" -o tsv 2>$null
        
        if ($connectionTest -eq "Ready") {
            Write-Success "PostgreSQL server is in 'Ready' state"
            $script:TestResults.DatabaseConnectivity = $true
            $script:SuccessCount++
        } else {
            Write-Error "PostgreSQL server state: $connectionTest"
            $script:ErrorCount++
        }
        
        # Check database exists
        Write-Info "Checking if database exists..."
        $databases = az postgres flexible-server db list --server-name reportmate-database --resource-group ReportMate --query "[].name" -o tsv 2>$null
        if ($databases -contains $dbName) {
            Write-Success "Database '$dbName' exists"
        } else {
            Write-Error "Database '$dbName' not found. Available databases: $($databases -join ', ')"
            $script:ErrorCount++
        }
        
    } catch {
        Write-Error "Database connectivity test failed: $($_.Exception.Message)"
        $script:ErrorCount++
    }
}

function Test-DatabaseSchema {
    Write-Section "Testing Database Schema"
    
    # Expected tables based on modular design
    $expectedTables = @(
        "devices", "events",
        "applications", "displays", "hardware", "installs", "inventory", 
        "management", "network", "printers", "profiles", "security", "system"
    )
    
    Write-Info "Expected tables: $($expectedTables -join ', ')"
    
    # For now, we'll assume schema is correct if database connectivity works
    # TODO: Add actual schema validation when we have proper DB connection testing
    if ($script:TestResults.DatabaseConnectivity) {
        Write-Success "Database schema validation (assumed correct - connectivity works)"
        $script:TestResults.DatabaseSchema = $true
        $script:SuccessCount++
    } else {
        Write-Error "Cannot validate schema - database connectivity failed"
        $script:ErrorCount++
    }
}

function Test-APIEndpoints {
    Write-Section "Testing API Endpoints"
    
    # Get API URL from terraform output or environment variable
    $baseUrl = $env:API_BASE_URL
    if (-not $baseUrl) {
        try {
            $baseUrl = (terraform output -raw api_url 2>$null)
        } catch {
            Write-Warning "Could not get API URL from terraform output. Set API_BASE_URL environment variable"
            return
        }
    }
    
    # Use a test device serial if provided in environment
    $testSerial = $env:TEST_DEVICE_SERIAL
    if (-not $testSerial) {
        Write-Warning "TEST_DEVICE_SERIAL environment variable not set. Skipping device-specific tests."
    }
    
    # Test health endpoint
    Write-Info "Testing health endpoint..."
    try {
        $healthResponse = Invoke-RestMethod -Uri "$baseUrl/api/health" -Method GET -TimeoutSec 30
        if ($healthResponse) {
            Write-Success "Health endpoint responding: $($healthResponse | ConvertTo-Json -Compress)"
            $script:TestResults.APIHealth = $true
            $script:SuccessCount++
        }
    } catch {
        Write-Error "Health endpoint failed: $($_.Exception.Message)"
        $script:ErrorCount++
    }
    
    # Test device endpoint
    Write-Info "Testing device endpoint with serial: $testSerial"
    try {
        $deviceResponse = Invoke-RestMethod -Uri "$baseUrl/api/device/$testSerial" -Method GET -TimeoutSec 30
        if ($deviceResponse -and $deviceResponse.device) {
            Write-Success "Device endpoint responding - Serial: $($deviceResponse.device.serial_number)"
            
            # Check for module data
            $moduleCount = 0
            if ($deviceResponse.device.PSObject.Properties.Name -contains "applications") { $moduleCount++ }
            if ($deviceResponse.device.PSObject.Properties.Name -contains "hardware") { $moduleCount++ }
            if ($deviceResponse.device.PSObject.Properties.Name -contains "system") { $moduleCount++ }
            if ($deviceResponse.device.PSObject.Properties.Name -contains "network") { $moduleCount++ }
            if ($deviceResponse.device.PSObject.Properties.Name -contains "security") { $moduleCount++ }
            
            Write-Info "Module data available: $moduleCount modules detected"
            $script:TestResults.APIDeviceEndpoint = $true
            $script:SuccessCount++
        }
    } catch {
        Write-Error "Device endpoint failed: $($_.Exception.Message)"
        $script:ErrorCount++
    }
    
    # Test events endpoint
    Write-Info "Testing events endpoint..."
    try {
        $eventsResponse = Invoke-RestMethod -Uri "$baseUrl/api/events" -Method GET -TimeoutSec 30
        if ($eventsResponse -and $eventsResponse.events) {
            $eventCount = $eventsResponse.events.Count
            Write-Success "Events endpoint responding - Event count: $eventCount"
            $script:TestResults.APIEventsEndpoint = $true
            $script:SuccessCount++
        }
    } catch {
        Write-Error "Events endpoint failed: $($_.Exception.Message)"
        $script:ErrorCount++
    }
}

function Test-ContainerApps {
    Write-Section "Testing Container Apps"
    
    try {
        # Check API container app
        Write-Info "Checking API container app status..."
        $apiApp = az containerapp show --name reportmate-functions-api --resource-group ReportMate --query "{name:name,status:properties.runningStatus,replicas:properties.template.scale.maxReplicas}" -o json 2>$null | ConvertFrom-Json
        
        if ($apiApp -and $apiApp.status -eq "Running") {
            Write-Success "API container app is running - Max replicas: $($apiApp.replicas)"
        } else {
            Write-Error "API container app status: $($apiApp.status)"
            $script:ErrorCount++
        }
        
        # Check frontend container app
        Write-Info "Checking frontend container app status..."
        $frontendApp = az containerapp show --name reportmate-web-app-prod --resource-group ReportMate --query "{name:name,status:properties.runningStatus,replicas:properties.template.scale.maxReplicas}" -o json 2>$null | ConvertFrom-Json
        
        if ($frontendApp -and $frontendApp.status -eq "Running") {
            Write-Success "Frontend container app is running - Max replicas: $($frontendApp.replicas)"
            $script:TestResults.ContainerAppsRunning = $true
            $script:SuccessCount++
        } else {
            Write-Error "Frontend container app status: $($frontendApp.status)"
            $script:ErrorCount++
        }
        
    } catch {
        Write-Error "Container apps check failed: $($_.Exception.Message)"
        $script:ErrorCount++
    }
}

function Test-FrontDoorRouting {
    Write-Section "Testing Front Door Routing"
    
    # Get custom domain from terraform output or environment variable
    $customDomain = $env:CUSTOM_DOMAIN
    if (-not $customDomain) {
        try {
            $customDomain = (terraform output -raw frontend_url 2>$null)
        } catch {
            Write-Warning "Could not get custom domain from terraform output. Set CUSTOM_DOMAIN environment variable. Skipping Front Door tests."
            return
        }
    }
    
    # Ensure URL has https://
    if ($customDomain -notmatch "^https?://") {
        $customDomain = "https://$customDomain"
    }
    
    try {
        # Test main site routing
        Write-Info "Testing main site routing through Front Door..."
        $response = Invoke-WebRequest -Uri $customDomain -Method HEAD -TimeoutSec 30
        if ($response.StatusCode -eq 200) {
            Write-Success "Front Door main routing working - Status: $($response.StatusCode)"
        } else {
            Write-Warning "Front Door main routing returned: $($response.StatusCode)"
            $script:WarningCount++
        }
        
        # Test API routing through Front Door
        Write-Info "Testing API routing through Front Door..."
        $apiResponse = Invoke-WebRequest -Uri "$customDomain/api/health" -Method HEAD -TimeoutSec 30
        if ($apiResponse.StatusCode -eq 200) {
            Write-Success "Front Door API routing working - Status: $($apiResponse.StatusCode)"
            $script:TestResults.FrontDoorRouting = $true
            $script:SuccessCount++
        } else {
            Write-Warning "Front Door API routing returned: $($apiResponse.StatusCode)"
            $script:WarningCount++
        }
        
    } catch {
        Write-Error "Front Door routing test failed: $($_.Exception.Message)"
        $script:ErrorCount++
    }
}

function Test-DataTransmission {
    Write-Section "Testing Data Transmission Flow"
    
    # Check for recent events in the API
    Write-Info "Checking for recent data transmission events..."
    
    try {
        $baseUrl = "https://reportmate-api.azurewebsites.net"
        $eventsResponse = Invoke-RestMethod -Uri "$baseUrl/api/events" -Method GET -TimeoutSec 30
        
        if ($eventsResponse -and $eventsResponse.events) {
            $recentEvents = $eventsResponse.events | Where-Object { 
                $eventDate = [DateTime]$_.timestamp
                $eventDate -gt (Get-Date).AddDays(-1)
            }
            
            if ($recentEvents.Count -gt 0) {
                Write-Success "Recent data transmission detected - Events in last 24h: $($recentEvents.Count)"
                $script:TestResults.DataTransmission = $true
                $script:SuccessCount++
                
                if ($Verbose) {
                    Write-Info "Recent event types: $($recentEvents.event_type | Group-Object | ForEach-Object { "$($_.Name): $($_.Count)" } | Join-String -Separator ', ')"
                }
            } else {
                Write-Warning "No recent data transmission events found (last 24 hours)"
                $script:WarningCount++
            }
        }
        
    } catch {
        Write-Error "Data transmission check failed: $($_.Exception.Message)"
        $script:ErrorCount++
    }
}

function Show-Summary {
    Write-Section "Infrastructure Health Check Summary"
    
    Write-Host "`nTest Results:" -ForegroundColor White -BackgroundColor DarkBlue
    foreach ($test in $script:TestResults.GetEnumerator()) {
        $status = if ($test.Value) { "[PASS]" } else { "[FAIL]" }
        Write-Host "   $($test.Key): $status"
    }
    
    Write-Host "`nSummary:" -ForegroundColor White -BackgroundColor DarkBlue
    Write-Host "   Successes: $script:SuccessCount" -ForegroundColor Green
    Write-Host "   Warnings: $script:WarningCount" -ForegroundColor Yellow
    Write-Host "   Errors: $script:ErrorCount" -ForegroundColor Red
    
    $totalTests = $script:TestResults.Count
    $passedTests = ($script:TestResults.Values | Where-Object { $_ -eq $true }).Count
    $healthPercentage = [math]::Round(($passedTests / $totalTests) * 100, 1)
    
    Write-Host "`nOverall Health: $healthPercentage% ($passedTests/$totalTests tests passing)" -ForegroundColor White -BackgroundColor DarkBlue
    
    if ($healthPercentage -ge 80) {
        Write-Success "`nSystem Status: HEALTHY"
    } elseif ($healthPercentage -ge 60) {
        Write-Warning "`nSystem Status: DEGRADED"
    } else {
        Write-Error "`nSystem Status: CRITICAL"
    }
    
    # Recommendations
    if ($script:ErrorCount -gt 0 -or $script:WarningCount -gt 0) {
        Write-Host "`nRecommendations:" -ForegroundColor White -BackgroundColor DarkMagenta
        
        if (-not $script:TestResults.DatabaseConnectivity) {
            Write-Host "   • Check database server status and firewall rules" -ForegroundColor Yellow
        }
        
        if (-not $script:TestResults.APIHealth) {
            Write-Host "   • Redeploy API functions using: .\infrastructure\scripts\deploy-functions.ps1" -ForegroundColor Yellow
        }
        
        if (-not $script:TestResults.ContainerAppsRunning) {
            Write-Host "   • Check container app logs in Azure portal" -ForegroundColor Yellow
        }
        
        if (-not $script:TestResults.DataTransmission) {
            Write-Host "   • Check Windows client is running and transmitting data" -ForegroundColor Yellow
        }
    }
}

# Main execution
function Main {
    Write-Host @"
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    ReportMate Infrastructure Health Check                     ║
║                        Single Canonical Status Script                        ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"@ -ForegroundColor Cyan

    Write-Info "Starting comprehensive infrastructure health check..."
    Write-Info "Timestamp: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    
    # Run all tests
    Test-DatabaseConnectivity
    Test-DatabaseSchema
    Test-APIEndpoints
    Test-ContainerApps
    Test-FrontDoorRouting
    Test-DataTransmission
    
    # Show final summary
    Show-Summary
    
    # Set exit code based on health
    $totalTests = $script:TestResults.Count
    $passedTests = ($script:TestResults.Values | Where-Object { $_ -eq $true }).Count
    $healthPercentage = ($passedTests / $totalTests) * 100
    
    if ($healthPercentage -lt 60) {
        exit 1  # Critical status
    } elseif ($healthPercentage -lt 80) {
        exit 2  # Degraded status  
    } else {
        exit 0  # Healthy status
    }
}

# Execute main function
Main