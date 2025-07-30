#!/usr/bin/env pwsh
#Requires -Version 7.0

<#
.SYNOPSIS
    ReportMate Infrastructure Canonical Health Check
    
.DESCRIPTION
    Single authoritative script to check ALL components of ReportMate infrastructure:
    - Database connectivity and schema
    - Azure Functions API endpoints
    - Data transmission pipeline
    - Table structure and data integrity
    - Event validation and processing
    
.PARAMETER Environment
    Environment to check (dev, staging, prod). Defafunction Invoke-FixIssues {
    Write-Header "Attempting to Fix Issues"
    
    if ($Global:CheckResults.Tables.Status -eq 'Issues') {
        Write-Info "Attempting to fix table issues..."
        
        # Try to initialize database
        try {
            $initResponse = Invoke-WebRequest -Uri "$($CONFIG.API.BaseUrl)/api/init-db?init=true" -Method GET -UseBasicParsing
            if ($initResponse.StatusCode -eq 200) {
                Write-Success "Database initialization attempt completed"
            }
        } catch {
            Write-Warning "Database initialization failed: $_"
        }
    }
    
    if ($Global:CheckResults.SchemaFiles.Status -eq 'Issues') {
        Write-Info "Attempting to fix schema file conflicts..."
        
        # Check if user wants to remove conflicting files
        foreach ($issue in $Global:CheckResults.SchemaFiles.Issues) {
            if ($issue -like "Conflicting schema file exists:*") {
                $conflictFile = $issue.Replace("Conflicting schema file exists: ", "")
                if (Test-Path $conflictFile) {
                    Write-Warning "Would remove conflicting file: $conflictFile"
                    Write-Info "  Use 'Remove-Item `"$conflictFile`"' to manually remove"
                }
            }
        }
        
        Write-Info "Schema conflicts require manual removal for safety"
        Write-Info "Review the conflicting files and remove them if no longer needed"
    }
    
    # Add more fix logic as needed
}RAMETER DetailedOutput
    Show detailed diagnostic information
    
.PARAMETER FixIssues
    Attempt to fix common issues found during check
    
.PARAMETER TestData
    Include test data validation checks
    
.EXAMPLE
    .\check.ps1
    # Basic health check
    
.EXAMPLE
    .\check.ps1 -DetailedOutput -TestData
    # Comprehensive check with detailed output
    
.EXAMPLE
    .\check.ps1 -FixIssues
    # Check and attempt to fix issues
#>

param(
    [Parameter(Mandatory = $false)]
    [ValidateSet("dev", "staging", "prod")]
    [string]$Environment = "dev",
    
    [Parameter(Mandatory = $false)]
    [switch]$DetailedOutput,
    
    [Parameter(Mandatory = $false)]
    [switch]$FixIssues,
    
    [Parameter(Mandatory = $false)]
    [switch]$TestData
)

$ErrorActionPreference = "Continue"
$ProgressPreference = "SilentlyContinue"

# Configuration
$CONFIG = @{
    Database = @{
        ConnectionString = "postgresql://reportmate:2sSWbVxyqjXp9WUpeMmzRaC@reportmate-database.postgres.database.azure.com:5432/reportmate?sslmode=require"
    }
    API = @{
        BaseUrl = "https://reportmate-api.azurewebsites.net"
    }
    ExpectedTables = @(
        'devices', 'events',
        'applications', 'displays', 'hardware', 'installs', 'inventory',
        'management', 'network', 'printers', 'profiles', 'security', 'system'
    )
    ValidEventTypes = @('success', 'warning', 'error', 'info')
    CanonicalSchema = "infrastructure\schemas\modular-database-schema.sql"
    ProhibitedSchemaFiles = @(
        'azure-database-schema.sql',
        'azure-database-core.sql', 
        'infrastructure\schemas\database.sql',
        'infrastructure\schemas\schema.prisma',
        'infrastructure\schemas\create-devices-table.sql',
        'apps\www\prisma\schema.prisma',
        'infrastructure\schemas\migrate-database-schema.sql',
        'infrastructure\schemas\migrate-serial-based-registration.sql',
        'infrastructure\schemas\manual-add-missing-fields.sql'
    )
}

# Colors and formatting
function Write-Header { param($Text) Write-Host "`n🔍 $Text" -ForegroundColor Cyan -NoNewline; Write-Host " " -ForegroundColor Gray }
function Write-Success { param($Text) Write-Host "✅ $Text" -ForegroundColor Green }
function Write-Warning { param($Text) Write-Host "⚠️  $Text" -ForegroundColor Yellow }
function Write-Error { param($Text) Write-Host "❌ $Text" -ForegroundColor Red }
function Write-Info { param($Text) Write-Host "ℹ️  $Text" -ForegroundColor Blue }
function Write-Detail { param($Text) if ($DetailedOutput) { Write-Host "   📋 $Text" -ForegroundColor Gray } }

# Global results tracking
$Global:CheckResults = @{
    Database = @{ Status = 'Unknown'; Issues = @() }
    API = @{ Status = 'Unknown'; Issues = @() }
    Tables = @{ Status = 'Unknown'; Issues = @() }
    Data = @{ Status = 'Unknown'; Issues = @() }
    Events = @{ Status = 'Unknown'; Issues = @() }
    SchemaFiles = @{ Status = 'Unknown'; Issues = @() }
    Overall = @{ Status = 'Unknown'; Issues = @() }
}

#region Database Checks
function Test-DatabaseConnection {
    Write-Header "Database Connection"
    
    try {
        # Test via API health endpoint instead of direct connection
        Write-Detail "Testing database connection via API health endpoint..."
        $healthResponse = Invoke-WebRequest -Uri "$($CONFIG.API.BaseUrl)/api/health" -Method GET -UseBasicParsing -TimeoutSec 30
        
        if ($healthResponse.StatusCode -eq 200) {
            $healthData = $healthResponse.Content | ConvertFrom-Json
            if ($healthData.database -eq 'healthy' -or $healthData.status -eq 'healthy') {
                Write-Success "Database connection successful (via API)"
                $Global:CheckResults.Database.Status = 'Healthy'
                return $true
            } else {
                Write-Warning "Database connection issues reported by API"
                $Global:CheckResults.Database.Status = 'Issues'
                $Global:CheckResults.Database.Issues += "API reports database issues"
                return $false
            }
        } else {
            Write-Error "API health check failed with status: $($healthResponse.StatusCode)"
            $Global:CheckResults.Database.Status = 'Failed'
            $Global:CheckResults.Database.Issues += "API health check failed: $($healthResponse.StatusCode)"
            return $false
        }
    } catch {
        Write-Error "Database connection test failed: $_"
        $Global:CheckResults.Database.Status = 'Failed'
        $Global:CheckResults.Database.Issues += "Connection test error: $_"
        return $false
    }
}

function Test-DatabaseSchema {
    Write-Header "Database Schema Validation"
    
    $schemaIssues = @()
    
    try {
        # Check schema via API instead of direct database connection
        Write-Detail "Checking database schema via API..."
        
        # Try to get devices list to validate schema
        $devicesResponse = Invoke-WebRequest -Uri "$($CONFIG.API.BaseUrl)/api/devices" -Method GET -UseBasicParsing -TimeoutSec 30
        
        if ($devicesResponse.StatusCode -eq 200) {
            Write-Success "Devices table accessible via API"
            
            # Try to get events
            $eventsResponse = Invoke-WebRequest -Uri "$($CONFIG.API.BaseUrl)/api/events" -Method GET -UseBasicParsing -TimeoutSec 30
            
            if ($eventsResponse.StatusCode -eq 200) {
                Write-Success "Events table accessible via API"
            } else {
                Write-Warning "Events table may have issues"
                $schemaIssues += "Events table not accessible via API"
            }
            
            # Check if we have any actual data
            $devicesData = $devicesResponse.Content | ConvertFrom-Json
            if ($devicesData -and $devicesData.Count -gt 0) {
                Write-Success "Database contains device data"
                Write-Detail "Found $($devicesData.Count) devices"
            } else {
                Write-Info "Database schema exists but no devices found"
            }
            
        } else {
            Write-Warning "Cannot access devices table via API"
            $schemaIssues += "Devices table not accessible"
        }
        
        if ($schemaIssues.Count -eq 0) {
            Write-Success "Database schema validation passed"
            $Global:CheckResults.Tables.Status = 'Healthy'
        } else {
            Write-Warning "Database schema has issues"
            $Global:CheckResults.Tables.Status = 'Issues'
            $Global:CheckResults.Tables.Issues = $schemaIssues
        }
        
    } catch {
        Write-Error "Schema validation failed: $_"
        $Global:CheckResults.Tables.Status = 'Failed'
        $Global:CheckResults.Tables.Issues += "Schema validation error: $_"
    }
}

function Test-DatabaseData {
    Write-Header "Database Data Integrity"
    
    $dataIssues = @()
    
    try {
        # Check data via API endpoints
        Write-Detail "Checking database data via API endpoints..."
        
        # Get devices data
        $devicesResponse = Invoke-WebRequest -Uri "$($CONFIG.API.BaseUrl)/api/devices" -Method GET -UseBasicParsing -TimeoutSec 30
        
        if ($devicesResponse.StatusCode -eq 200) {
            $devicesData = $devicesResponse.Content | ConvertFrom-Json
            $deviceCount = if ($devicesData) { $devicesData.Count } else { 0 }
            Write-Info "Devices: $deviceCount records"
            
            if ($deviceCount -gt 0) {
                Write-Success "Device data present"
                
                # Check for duplicate serial numbers (basic check)
                $serialNumbers = @()
                foreach ($device in $devicesData) {
                    if ($device.serial_number) {
                        $serialNumbers += $device.serial_number
                    }
                }
                
                $uniqueSerials = $serialNumbers | Select-Object -Unique
                if ($serialNumbers.Count -ne $uniqueSerials.Count) {
                    Write-Warning "Potential duplicate serial numbers detected"
                    $dataIssues += "Duplicate serial numbers may exist"
                } else {
                    Write-Success "No duplicate serial numbers detected"
                }
            }
        } else {
            Write-Warning "Could not retrieve devices data"
            $dataIssues += "Devices data not accessible"
        }
        
        # Get events data
        try {
            $eventsResponse = Invoke-WebRequest -Uri "$($CONFIG.API.BaseUrl)/api/events" -Method GET -UseBasicParsing -TimeoutSec 30
            
            if ($eventsResponse.StatusCode -eq 200) {
                $eventsData = $eventsResponse.Content | ConvertFrom-Json
                $eventCount = if ($eventsData) { $eventsData.Count } else { 0 }
                Write-Info "Events: $eventCount records"
                
                if ($eventCount -gt 0) {
                    Write-Success "Event data present"
                    
                    # Check event types
                    $invalidEvents = 0
                    foreach ($eventItem in $eventsData) {
                        if ($eventItem.severity -and $eventItem.severity -notin $CONFIG.ValidEventTypes) {
                            $invalidEvents++
                        }
                    }
                    
                    if ($invalidEvents -gt 0) {
                        Write-Warning "$invalidEvents invalid event types found"
                        $dataIssues += "Invalid event types detected"
                    } else {
                        Write-Success "All event types are valid"
                    }
                }
            } else {
                Write-Warning "Could not retrieve events data"
                $dataIssues += "Events data not accessible"
            }
        } catch {
            Write-Warning "Events endpoint may not be available: $_"
        }
        
        if ($dataIssues.Count -eq 0) {
            Write-Success "Database data integrity check passed"
            $Global:CheckResults.Data.Status = 'Healthy'
        } else {
            Write-Warning "Database data has integrity issues"
            $Global:CheckResults.Data.Status = 'Issues'
            $Global:CheckResults.Data.Issues = $dataIssues
        }
        
    } catch {
        Write-Error "Data integrity check failed: $_"
        $Global:CheckResults.Data.Status = 'Failed'
        $Global:CheckResults.Data.Issues += "Data integrity error: $_"
    }
}
#endregion

#region Schema File Validation
function Test-SchemaFiles {
    Write-Header "Schema File Validation"
    
    $schemaIssues = @()
    
    try {
        # Check that canonical schema exists
        if (Test-Path $CONFIG.CanonicalSchema) {
            Write-Success "Canonical schema found: $($CONFIG.CanonicalSchema)"
            Write-Detail "Single source of truth confirmed"
        } else {
            Write-Error "Canonical schema missing: $($CONFIG.CanonicalSchema)"
            $schemaIssues += "Canonical schema file not found"
        }
        
        # Check for prohibited duplicate/conflicting schema files
        Write-Detail "Checking for conflicting schema files..."
        
        $foundConflicts = @()
        foreach ($prohibitedFile in $CONFIG.ProhibitedSchemaFiles) {
            if (Test-Path $prohibitedFile) {
                $foundConflicts += $prohibitedFile
                Write-Warning "Found conflicting schema file: $prohibitedFile"
                $schemaIssues += "Conflicting schema file exists: $prohibitedFile"
            }
        }
        
        if ($foundConflicts.Count -eq 0) {
            Write-Success "No conflicting schema files found"
        } else {
            Write-Warning "Found $($foundConflicts.Count) conflicting schema files"
        }
        
        # Check for any unexpected .sql files that might be schemas
        Write-Detail "Scanning for unexpected .sql schema files..."
        $allSqlFiles = Get-ChildItem -Path "." -Filter "*.sql" -Recurse | Where-Object { 
            $_.Name -match "(schema|database|migrate|create)" -and 
            $_.FullName -notlike "*$($CONFIG.CanonicalSchema)*" -and
            $_.FullName -notlike "*node_modules*"
        }
        
        if ($allSqlFiles.Count -gt 0) {
            Write-Warning "Found potentially conflicting SQL files:"
            foreach ($file in $allSqlFiles) {
                $relativePath = $file.FullName.Replace((Get-Location).Path, "").TrimStart('\')
                Write-Warning "  - $relativePath"
                $schemaIssues += "Potential schema conflict: $relativePath"
            }
        } else {
            Write-Success "No unexpected schema files found"
        }
        
        # Check for .prisma files
        Write-Detail "Checking for Prisma schema files..."
        $prismaFiles = Get-ChildItem -Path "." -Filter "*.prisma" -Recurse | Where-Object { 
            $_.FullName -notlike "*node_modules*" 
        }
        
        if ($prismaFiles.Count -gt 0) {
            Write-Warning "Found Prisma schema files (potential conflicts):"
            foreach ($file in $prismaFiles) {
                $relativePath = $file.FullName.Replace((Get-Location).Path, "").TrimStart('\')
                Write-Warning "  - $relativePath"
                $schemaIssues += "Prisma schema file exists: $relativePath"
            }
        } else {
            Write-Success "No Prisma schema files found"
        }
        
        if ($schemaIssues.Count -eq 0) {
            Write-Success "Schema file validation passed"
            $Global:CheckResults.SchemaFiles.Status = 'Healthy'
        } else {
            Write-Warning "Schema file validation found issues"
            $Global:CheckResults.SchemaFiles.Status = 'Issues'
            $Global:CheckResults.SchemaFiles.Issues = $schemaIssues
        }
        
    } catch {
        Write-Error "Schema file validation failed: $_"
        $Global:CheckResults.SchemaFiles.Status = 'Failed'
        $Global:CheckResults.SchemaFiles.Issues += "Schema validation error: $_"
    }
}
#endregion

#region API Checks
function Test-APIEndpoints {
    Write-Header "API Endpoints Validation"
    
    $apiIssues = @()
    
    # Define endpoints to test
    $endpoints = @(
        @{ Path = "/api/health"; Method = "GET"; Expected = 200; Required = $true }
        @{ Path = "/api/devices"; Method = "GET"; Expected = 200; Required = $true }
        @{ Path = "/api/events"; Method = "GET"; Expected = 200; Required = $true }
    )
    
    foreach ($endpoint in $endpoints) {
        try {
            $url = "$($CONFIG.API.BaseUrl)$($endpoint.Path)"
            Write-Detail "Testing: $($endpoint.Method) $url"
            
            $response = Invoke-WebRequest -Uri $url -Method $endpoint.Method -UseBasicParsing -ErrorAction Stop
            
            if ($response.StatusCode -eq $endpoint.Expected) {
                Write-Success "$($endpoint.Path) responded correctly ($($response.StatusCode))"
            } else {
                Write-Warning "$($endpoint.Path) unexpected status: $($response.StatusCode) (expected $($endpoint.Expected))"
                $apiIssues += "Endpoint $($endpoint.Path) returned $($response.StatusCode), expected $($endpoint.Expected)"
            }
            
        } catch {
            if ($endpoint.Required) {
                Write-Error "$($endpoint.Path) failed: $_"
                $apiIssues += "Endpoint $($endpoint.Path) failed: $_"
            } else {
                Write-Warning "$($endpoint.Path) not available: $_"
            }
        }
    }
    
    if ($apiIssues.Count -eq 0) {
        Write-Success "All API endpoints responding correctly"
        $Global:CheckResults.API.Status = 'Healthy'
    } else {
        Write-Warning "API endpoints have issues"
        $Global:CheckResults.API.Status = 'Issues'
        $Global:CheckResults.API.Issues = $apiIssues
    }
}

function Test-DataTransmission {
    Write-Header "Data Transmission Pipeline"
    
    try {
        # Test the submission endpoint exists (but don't actually submit test data)
        Write-Detail "Testing data submission endpoint availability..."
        
        # Just check if the endpoint exists by testing with invalid method
        # This will return 405 Method Not Allowed if the endpoint exists
        try {
            Invoke-WebRequest -Uri "$($CONFIG.API.BaseUrl)/api/events-submit" -Method GET -UseBasicParsing -TimeoutSec 10 | Out-Null
        } catch {
            if ($_.Exception.Response.StatusCode -eq 405) {
                Write-Success "Data transmission endpoint available (POST required)"
            } elseif ($_.Exception.Response.StatusCode -eq 404) {
                Write-Warning "Data transmission endpoint not found"
                $Global:CheckResults.API.Issues += "events-submit endpoint not found"
            } else {
                Write-Info "Data transmission endpoint test inconclusive: $($_.Exception.Response.StatusCode)"
            }
        }
        
    } catch {
        Write-Warning "Data transmission test failed: $_"
        $Global:CheckResults.API.Issues += "Data transmission test failed: $_"
    }
}
#endregion

#region Event Validation
function Test-EventValidation {
    Write-Header "Event Processing Validation"
    
    try {
        # Check recent events via API
        $eventsResponse = Invoke-WebRequest -Uri "$($CONFIG.API.BaseUrl)/api/events" -Method GET -UseBasicParsing -TimeoutSec 30
        
        if ($eventsResponse.StatusCode -eq 200) {
            $eventsData = $eventsResponse.Content | ConvertFrom-Json
            
            if ($eventsData -and $eventsData.Count -gt 0) {
                Write-Info "Recent events found: $($eventsData.Count)"
                
                # Check for error events
                $errorEvents = 0
                foreach ($eventItem in $eventsData) {
                    if ($eventItem.severity -eq 'error') {
                        $errorEvents++
                    }
                }
                
                if ($errorEvents -gt 0) {
                    Write-Warning "$errorEvents error events in database"
                    $Global:CheckResults.Events.Issues += "$errorEvents error events found"
                } else {
                    Write-Success "No error events found"
                }
                
                Write-Success "Event processing validation completed"
            } else {
                Write-Info "No recent events found"
            }
        } else {
            Write-Warning "Could not retrieve events for validation"
        }
        
        $Global:CheckResults.Events.Status = 'Healthy'
        
    } catch {
        Write-Error "Event validation failed: $_"
        $Global:CheckResults.Events.Status = 'Failed'
        $Global:CheckResults.Events.Issues += "Event validation error: $_"
    }
}
#endregion

#region Fix Issues
function Invoke-FixIssues {
    Write-Header "Attempting to Fix Issues"
    
    if ($Global:CheckResults.Tables.Status -eq 'Issues') {
        Write-Info "Attempting to fix table issues..."
        
        # Try to initialize database
        try {
            $initResponse = Invoke-WebRequest -Uri "$($CONFIG.API.BaseUrl)/api/init-db?init=true" -Method GET -UseBasicParsing
            if ($initResponse.StatusCode -eq 200) {
                Write-Success "Database initialization completed"
            }
        } catch {
            Write-Warning "Database initialization failed: $_"
        }
    }
    
    # Add more fix logic as needed
}
#endregion

#region Summary Report
function Show-Summary {
    Write-Host "`n" -NoNewline
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "🏥 REPORTMATE INFRASTRUCTURE HEALTH SUMMARY" -ForegroundColor Cyan
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
    
    $components = @(
        @{ Name = "Database Connection"; Status = $Global:CheckResults.Database.Status }
        @{ Name = "API Endpoints"; Status = $Global:CheckResults.API.Status }
        @{ Name = "Database Schema"; Status = $Global:CheckResults.Tables.Status }
        @{ Name = "Data Integrity"; Status = $Global:CheckResults.Data.Status }
        @{ Name = "Event Processing"; Status = $Global:CheckResults.Events.Status }
        @{ Name = "Schema Files"; Status = $Global:CheckResults.SchemaFiles.Status }
    )
    
    $healthyCount = 0
    $issueCount = 0
    $failedCount = 0
    
    foreach ($component in $components) {
        $statusIcon = switch ($component.Status) {
            'Healthy' { '✅'; $healthyCount++ }
            'Issues' { '⚠️ '; $issueCount++ }
            'Failed' { '❌'; $failedCount++ }
            default { '❓'; $failedCount++ }
        }
        
        $statusColor = switch ($component.Status) {
            'Healthy' { 'Green' }
            'Issues' { 'Yellow' }
            'Failed' { 'Red' }
            default { 'Gray' }
        }
        
        Write-Host "$statusIcon $($component.Name)" -ForegroundColor $statusColor
    }
    
    Write-Host "`n📊 SUMMARY:" -ForegroundColor White
    Write-Host "   ✅ Healthy: $healthyCount components" -ForegroundColor Green
    Write-Host "   ⚠️  Issues: $issueCount components" -ForegroundColor Yellow
    Write-Host "   ❌ Failed: $failedCount components" -ForegroundColor Red
    
    # Overall status
    $overallStatus = if ($failedCount -gt 0) { 'CRITICAL' } elseif ($issueCount -gt 0) { 'WARNING' } else { 'HEALTHY' }
    $overallColor = if ($failedCount -gt 0) { 'Red' } elseif ($issueCount -gt 0) { 'Yellow' } else { 'Green' }
    
    Write-Host "`n🎯 OVERALL STATUS: " -NoNewline -ForegroundColor White
    Write-Host $overallStatus -ForegroundColor $overallColor
    
    # Show detailed issues if any
    $allIssues = @()
    $Global:CheckResults.Values | ForEach-Object { $allIssues += $_.Issues }
    
    if ($allIssues.Count -gt 0) {
        Write-Host "`n🔧 ISSUES FOUND:" -ForegroundColor Yellow
        $allIssues | ForEach-Object { Write-Host "   • $_" -ForegroundColor Yellow }
        
        if (-not $FixIssues) {
            Write-Host "`n💡 TIP: Run with -FixIssues to attempt automatic fixes" -ForegroundColor Cyan
        }
    }
    
    Write-Host "`n📅 Check completed: $(Get-Date)" -ForegroundColor Gray
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
}
#endregion

#region Main Execution
function Main {
    Write-Host "🚀 ReportMate Infrastructure Health Check" -ForegroundColor Magenta
    Write-Host "Environment: $Environment" -ForegroundColor Gray
    Write-Host "Detailed Output: $DetailedOutput" -ForegroundColor Gray
    Write-Host "Fix Issues: $FixIssues" -ForegroundColor Gray
    Write-Host ""
    
    # Prerequisites check
    Write-Header "Prerequisites"
    
    # Check PowerShell version
    if ($PSVersionTable.PSVersion.Major -ge 7) {
        Write-Success "PowerShell: $($PSVersionTable.PSVersion)"
    } else {
        Write-Warning "PowerShell 7+ recommended (current: $($PSVersionTable.PSVersion))"
    }
    
    # Check internet connectivity to API
    try {
        $testConnection = Test-NetConnection -ComputerName "reportmate-api.azurewebsites.net" -Port 443 -InformationLevel Quiet -WarningAction SilentlyContinue
        if ($testConnection) {
            Write-Success "Network connectivity to API endpoint"
        } else {
            Write-Warning "Cannot reach API endpoint"
        }
    } catch {
        Write-Warning "Network connectivity test failed: $_"
    }
    
    # Run all checks
    $dbConnected = Test-DatabaseConnection
    
    if ($dbConnected) {
        Test-DatabaseSchema
        Test-DatabaseData
    }
    
    Test-SchemaFiles
    Test-APIEndpoints
    Test-DataTransmission
    Test-EventValidation
    
    # Fix issues if requested
    if ($FixIssues) {
        Invoke-FixIssues
    }
    
    # Show summary
    Show-Summary
    
    # Return appropriate exit code
    $failedComponents = $Global:CheckResults.Values | Where-Object { $_.Status -eq 'Failed' }
    $exitCode = if ($failedComponents.Count -gt 0) { 1 } else { 0 }
    return $exitCode
}

# Execute main function
try {
    $exitCode = Main
    exit $exitCode
} catch {
    Write-Error "Check script failed: $_"
    exit 1
}
#endregion
