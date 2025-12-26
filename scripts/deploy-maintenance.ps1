#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Build and deploy ReportMate database maintenance container

.DESCRIPTION
    Builds the maintenance container image, pushes to ACR, and optionally triggers a manual test run.

.PARAMETER SkipBuild
    Skip building the container image (use existing image)

.PARAMETER SkipPush
    Skip pushing to ACR (test build only)

.PARAMETER TestRun
    Trigger a manual test execution after deployment

.PARAMETER Tag
    Custom image tag (default: latest)

.EXAMPLE
    .\deploy-maintenance.ps1
    Build, push, and deploy maintenance container

.EXAMPLE
    .\deploy-maintenance.ps1 -TestRun
    Deploy and trigger manual test execution

.EXAMPLE
    .\deploy-maintenance.ps1 -SkipBuild -TestRun
    Use existing image and test
#>

param(
    [switch]$SkipBuild,
    [switch]$SkipPush,
    [switch]$TestRun,
    [string]$Tag = "latest"
)

$ErrorActionPreference = "Stop"

# Configuration
$ACR_NAME = "reportmateacr"
$IMAGE_NAME = "reportmate-maintenance"
$RESOURCE_GROUP = "ReportMate"
$JOB_NAME = "reportmate-db-maintenance"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "ReportMate Maintenance Container Deploy" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Change to maintenance module directory
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$MAINTENANCE_MODULE_DIR = Join-Path $SCRIPT_DIR "..\modules\maintenance"
Push-Location $MAINTENANCE_MODULE_DIR

try {
    # Verify Azure CLI is installed
    if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
        throw "Azure CLI not found. Please install: https://aka.ms/InstallAzureCLIDirect"
    }

    # Verify Docker is running
    if (-not $SkipBuild -and -not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw "Docker not found. Please install Docker Desktop."
    }

    # Check Azure login
    Write-Host "Checking Azure authentication..." -ForegroundColor Yellow
    $account = az account show 2>$null | ConvertFrom-Json
    if (-not $account) {
        throw "Not logged in to Azure. Run: az login"
    }
    Write-Host "  Logged in as: $($account.user.name)" -ForegroundColor Green
    Write-Host "  Subscription: $($account.name)`n" -ForegroundColor Green

    # Build container image
    if (-not $SkipBuild) {
        Write-Host "Building container image..." -ForegroundColor Yellow
        
        $imageFull = "$ACR_NAME.azurecr.io/${IMAGE_NAME}:${Tag}"
        
        docker build -t $imageFull . --no-cache
        
        if ($LASTEXITCODE -ne 0) {
            throw "Docker build failed"
        }
        
        Write-Host "  Built: $imageFull`n" -ForegroundColor Green
    }
    else {
        Write-Host "Skipping build (using existing image)`n" -ForegroundColor Yellow
    }

    # Push to ACR
    if (-not $SkipPush) {
        Write-Host "Logging in to Azure Container Registry..." -ForegroundColor Yellow
        az acr login --name $ACR_NAME
        
        if ($LASTEXITCODE -ne 0) {
            throw "ACR login failed"
        }
        
        Write-Host "  Logged in to $ACR_NAME.azurecr.io`n" -ForegroundColor Green

        Write-Host "Pushing image to ACR..." -ForegroundColor Yellow
        $imageFull = "$ACR_NAME.azurecr.io/${IMAGE_NAME}:${Tag}"
        
        docker push $imageFull
        
        if ($LASTEXITCODE -ne 0) {
            throw "Docker push failed"
        }
        
        Write-Host "  Pushed: $imageFull`n" -ForegroundColor Green
    }
    else {
        Write-Host "Skipping push to ACR`n" -ForegroundColor Yellow
    }

    # Verify job exists
    Write-Host "Verifying Container App Job..." -ForegroundColor Yellow
    $job = az containerapp job show `
        --name $JOB_NAME `
        --resource-group $RESOURCE_GROUP `
        2>$null | ConvertFrom-Json
    
    if (-not $job) {
        Write-Host "  Job not found. Run terraform apply to create it." -ForegroundColor Red
        Write-Host "`nTo create the job:" -ForegroundColor Yellow
        Write-Host "  cd ../../" -ForegroundColor Gray
        Write-Host "  terraform init" -ForegroundColor Gray
        Write-Host "  terraform apply`n" -ForegroundColor Gray
    }
    else {
        Write-Host "  Job found: $($job.name)" -ForegroundColor Green
        Write-Host "  Schedule: $($job.properties.configuration.scheduleTriggerConfig.cronExpression)`n" -ForegroundColor Green
    }

    # Trigger test run
    if ($TestRun) {
        if (-not $job) {
            throw "Cannot run test - job does not exist"
        }

        Write-Host "Triggering manual test execution..." -ForegroundColor Yellow
        
        $execution = az containerapp job start `
            --name $JOB_NAME `
            --resource-group $RESOURCE_GROUP `
            --output json | ConvertFrom-Json
        
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to start job execution"
        }
        
        $executionName = $execution.name
        Write-Host "  Started: $executionName" -ForegroundColor Green
        Write-Host "`nWaiting for execution to complete..." -ForegroundColor Yellow
        
        # Wait for completion (max 5 minutes)
        $timeout = 300
        $elapsed = 0
        $interval = 5
        
        while ($elapsed -lt $timeout) {
            Start-Sleep -Seconds $interval
            $elapsed += $interval
            
            $status = az containerapp job execution show `
                --name $JOB_NAME `
                --resource-group $RESOURCE_GROUP `
                --job-execution-name $executionName `
                --output json 2>$null | ConvertFrom-Json
            
            if ($status.properties.status -eq "Succeeded") {
                Write-Host "`n  Execution completed successfully!" -ForegroundColor Green
                break
            }
            elseif ($status.properties.status -eq "Failed") {
                Write-Host "`n  Execution failed!" -ForegroundColor Red
                break
            }
            
            Write-Host "." -NoNewline -ForegroundColor Gray
        }
        
        if ($elapsed -ge $timeout) {
            Write-Host "`n  Execution timed out after $timeout seconds" -ForegroundColor Yellow
        }
        
        Write-Host "`nFetching logs..." -ForegroundColor Yellow
        Write-Host "========================================`n" -ForegroundColor Gray
        
        az containerapp job logs show `
            --name $JOB_NAME `
            --resource-group $RESOURCE_GROUP `
            --format text `
            2>$null
        
        Write-Host "`n========================================" -ForegroundColor Gray
    }

    Write-Host "`nDeployment Summary:" -ForegroundColor Cyan
    Write-Host "  Image: $ACR_NAME.azurecr.io/${IMAGE_NAME}:${Tag}" -ForegroundColor White
    Write-Host "  Job: $JOB_NAME" -ForegroundColor White
    Write-Host "  Resource Group: $RESOURCE_GROUP" -ForegroundColor White
    
    if ($job) {
        Write-Host "  Next scheduled run: (check Azure Portal)" -ForegroundColor White
    }
    
    Write-Host "`nUseful Commands:" -ForegroundColor Cyan
    Write-Host "  Manual run:  " -NoNewline -ForegroundColor Gray
    Write-Host "az containerapp job start --name $JOB_NAME --resource-group $RESOURCE_GROUP" -ForegroundColor White
    
    Write-Host "  View logs:   " -NoNewline -ForegroundColor Gray
    Write-Host "az containerapp job logs show --name $JOB_NAME --resource-group $RESOURCE_GROUP --follow" -ForegroundColor White
    
    Write-Host "  List runs:   " -NoNewline -ForegroundColor Gray
    Write-Host "az containerapp job execution list --name $JOB_NAME --resource-group $RESOURCE_GROUP" -ForegroundColor White
    
    Write-Host "`nDone!`n" -ForegroundColor Green

}
catch {
    Write-Host "`nERROR: $_" -ForegroundColor Red
    exit 1
}
finally {
    Pop-Location
}
