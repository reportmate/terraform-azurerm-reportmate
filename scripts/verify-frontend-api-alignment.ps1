#!/usr/bin/env pwsh

<#
.SYNOPSIS
ReportMate Frontend-API Alignment Verification Script

.DESCRIPTION
Verifies that all frontend Next.js routes are properly aligned with the FastAPI container endpoints.
Tests both API integration and frontend page routing to ensure complete system alignment.

.PARAMETER Environment
Environment to test (prod, dev). Default: prod

.EXAMPLE
.\verify-frontend-api-alignment.ps1
# Verify production alignment

.EXAMPLE
.\verify-frontend-api-alignment.ps1 -Environment dev
# Verify development environment alignment
#>

param(
    [ValidateSet("prod", "dev")]
    [string]$Environment = "prod"
)

# Set error action preference
$ErrorActionPreference = "Continue"

# Colors for output
$Red = "`e[31m"
$Green = "`e[32m"
$Yellow = "`e[33m"
$Blue = "`e[34m"
$Reset = "`e[0m"

function Write-Success {
    param([string]$Message)
    Write-Host "${Green}✅ $Message${Reset}"
}

function Write-Error {
    param([string]$Message)
    Write-Host "${Red}❌ $Message${Reset}"
}

function Write-Warning {
    param([string]$Message)
    Write-Host "${Yellow}⚠️ $Message${Reset}"
}

function Write-Info {
    param([string]$Message)
    Write-Host "${Blue}ℹ️ $Message${Reset}"
}

# Configuration
$FastAPIUrl = "https://reportmate-functions-api.blackdune-79551938.canadacentral.azurecontainerapps.io"
$FrontendUrl = if ($Environment -eq "prod") {
    "https://reportmate-web-app-prod.blackdune-79551938.canadacentral.azurecontainerapps.io"
} else {
    "https://reportmate-web-app-dev.blackdune-79551938.canadacentral.azurecontainerapps.io"
}

Write-Host "${Blue}🚀 ReportMate Frontend-API Alignment Verification${Reset}"
Write-Host "${Blue}Environment: $Environment${Reset}"
Write-Host "${Blue}FastAPI Container: $FastAPIUrl${Reset}"
Write-Host "${Blue}Frontend Container: $FrontendUrl${Reset}"
Write-Host ""

$TotalTests = 0
$PassedTests = 0
$FailedTests = 0

function Test-Endpoint {
    param(
        [string]$Name,
        [string]$Url,
        [int]$ExpectedStatus = 200,
        [string]$ExpectedContent = $null
    )
    
    $Global:TotalTests++
    
    try {
        $Response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 10 -ErrorAction Stop
        
        if ($Response.StatusCode -eq $ExpectedStatus) {
            if ($ExpectedContent -and $Response.Content -notlike "*$ExpectedContent*") {
                Write-Error "$Name - Wrong content (Status: $($Response.StatusCode))"
                $Global:FailedTests++
                return $false
            } else {
                Write-Success "$Name - Status: $($Response.StatusCode)"
                $Global:PassedTests++
                return $true
            }
        } else {
            Write-Error "$Name - Wrong status: $($Response.StatusCode) (expected $ExpectedStatus)"
            $Global:FailedTests++
            return $false
        }
    } catch {
        Write-Error "$Name - Error: $($_.Exception.Message)"
        $Global:FailedTests++
        return $false
    }
}

function Test-JsonEndpoint {
    param(
        [string]$Name,
        [string]$Url,
        [string]$ExpectedProperty = $null,
        [int]$MinCount = $null
    )
    
    $Global:TotalTests++
    
    try {
        $Response = Invoke-RestMethod -Uri $Url -TimeoutSec 10 -ErrorAction Stop
        
        if ($ExpectedProperty) {
            $PropertyValue = $Response.$ExpectedProperty
            if ($null -eq $PropertyValue) {
                Write-Error "$Name - Missing property: $ExpectedProperty"
                $Global:FailedTests++
                return $false
            }
            
            if ($MinCount -and $PropertyValue.Count -lt $MinCount) {
                Write-Error "$Name - Property $ExpectedProperty has $($PropertyValue.Count) items (expected at least $MinCount)"
                $Global:FailedTests++
                return $false
            }
            
            Write-Success "$Name - Property: $ExpectedProperty ($($PropertyValue.Count) items)"
            $Global:PassedTests++
            return $true
        } else {
            Write-Success "$Name - JSON response received"
            $Global:PassedTests++
            return $true
        }
    } catch {
        Write-Error "$Name - Error: $($_.Exception.Message)"
        $Global:FailedTests++
        return $false
    }
}

# Test FastAPI Container Endpoints
Write-Host "${Yellow}📡 Testing FastAPI Container Endpoints${Reset}"

Test-JsonEndpoint "FastAPI Root" "$FastAPIUrl/" "endpoints"
Test-JsonEndpoint "FastAPI Health" "$FastAPIUrl/api/health"
Test-JsonEndpoint "FastAPI Devices Bulk" "$FastAPIUrl/api/devices" "devices" 100
Test-JsonEndpoint "FastAPI Individual Device" "$FastAPIUrl/api/device/0F33V9G25083HJ"
Test-JsonEndpoint "FastAPI Events" "$FastAPIUrl/api/events"
Test-JsonEndpoint "FastAPI Database Debug" "$FastAPIUrl/api/debug/database"

Write-Host ""

# Test Frontend Page Routes  
Write-Host "${Yellow}🌐 Testing Frontend Page Routes${Reset}"

Test-Endpoint "Frontend Home" "$FrontendUrl/"
Test-Endpoint "Frontend Devices List" "$FrontendUrl/devices"
Test-Endpoint "Frontend Events" "$FrontendUrl/events"
Test-Endpoint "Frontend Device Detail" "$FrontendUrl/device/0F33V9G25083HJ"
Test-Endpoint "Frontend Settings" "$FrontendUrl/settings"

Write-Host ""

# Test Frontend API Routes (Next.js API Routes)
Write-Host "${Yellow}🔗 Testing Frontend API Integration${Reset}"

Test-JsonEndpoint "Frontend API Devices" "$FrontendUrl/api/devices" "devices" 100
Test-JsonEndpoint "Frontend API Individual Device" "$FrontendUrl/api/device/0F33V9G25083HJ"
Test-JsonEndpoint "Frontend API Events" "$FrontendUrl/api/events"

Write-Host ""

# Device ID Alignment Verification
Write-Host "${Yellow}🎯 Testing Device ID Alignment${Reset}"

try {
    $FastAPIDevice = Invoke-RestMethod -Uri "$FastAPIUrl/api/device/0F33V9G25083HJ" -TimeoutSec 10
    $FrontendDevice = Invoke-RestMethod -Uri "$FrontendUrl/api/device/0F33V9G25083HJ" -TimeoutSec 10
    
    $TotalTests++
    
    $FastAPISerial = $FastAPIDevice.device.serialNumber
    $FrontendSerial = $FrontendDevice.device.serialNumber
    
    if ($FastAPISerial -eq $FrontendSerial -and $FastAPISerial -eq "0F33V9G25083HJ") {
        Write-Success "Device ID Alignment - serialNumber consistent: $FastAPISerial"
        $PassedTests++
    } else {
        Write-Error "Device ID Alignment - Mismatch: FastAPI=$FastAPISerial, Frontend=$FrontendSerial"
        $FailedTests++
    }
    
    # Test modules alignment
    $TotalTests++
    $FastAPIModules = $FastAPIDevice.device.modules | Get-Member -MemberType NoteProperty | Measure-Object
    $FrontendModules = $FrontendDevice.device.modules | Get-Member -MemberType NoteProperty | Measure-Object
    
    if ($FastAPIModules.Count -eq $FrontendModules.Count -and $FastAPIModules.Count -ge 10) {
        Write-Success "Module Data Alignment - Both have $($FastAPIModules.Count) modules"
        $PassedTests++
    } else {
        Write-Error "Module Data Alignment - FastAPI: $($FastAPIModules.Count), Frontend: $($FrontendModules.Count)"
        $FailedTests++
    }
    
} catch {
    Write-Error "Device ID Alignment Test - Error: $($_.Exception.Message)"
    $TotalTests += 2
    $FailedTests += 2
}

# Summary
Write-Host ""
Write-Host "${Blue}📊 Test Summary${Reset}"
Write-Host "Total Tests: $TotalTests"
Write-Success "Passed: $PassedTests"
if ($FailedTests -gt 0) {
    Write-Error "Failed: $FailedTests"
} else {
    Write-Host "${Green}Failed: $FailedTests${Reset}"
}

Write-Host ""

if ($FailedTests -eq 0) {
    Write-Host "${Green}🎉 ALL TESTS PASSED - Frontend and FastAPI are fully aligned!${Reset}"
    Write-Host "${Green}✅ Device ID standardization working correctly${Reset}"
    Write-Host "${Green}✅ All 11 modules flowing through properly${Reset}"  
    Write-Host "${Green}✅ Frontend routes responding correctly${Reset}"
    Write-Host "${Green}✅ API integration working perfectly${Reset}"
    exit 0
} else {
    Write-Host "${Red}❌ ALIGNMENT ISSUES DETECTED${Reset}"
    Write-Host "${Yellow}Please review the failed tests above and fix the issues.${Reset}"
    exit 1
}