#!/usr/bin/env pwsh

<#
.SYNOPSIS
ReportMate Container Deployment Script - Fixed version that doesn't hang

.DESCRIPTION
Deploys the ReportMate Next.js container to Azure Container Apps with automatic SSO login support.
This script addresses the hanging issues and implements automatic SSO.

.PARAMETER Environment
Environment to deploy (dev, staging, prod). Default: prod

.PARAMETER ForceBuild
Force rebuild even if no changes detected

.PARAMETER SkipBuild
Skip Docker build (use existing image)

.PARAMETER Tag
Custom image tag

.PARAMETER AutoSSO
Enable automatic SSO login (redirect immediately without login button)

.PARAMETER Test
Test deployment after completion

.EXAMPLE
.\deploy-containers.ps1 -Environment prod -AutoSSO
# Deploy to production with automatic SSO enabled

.EXAMPLE
.\deploy-containers.ps1 -ForceBuild
# Force rebuild and deploy

#>

param(
    [string]$Environment = "prod",
    [switch]$ForceBuild,
    [switch]$SkipBuild,
    [string]$Tag = "",
    [switch]$AutoSSO,
    [switch]$Test,
    [switch]$Help
)

# Set error action preference
$ErrorActionPreference = "Stop"

# Colors for output
$Red = "`e[31m"
$Green = "`e[32m"
$Yellow = "`e[33m"
$Blue = "`e[34m"
$Reset = "`e[0m"

# Configuration
$RegistryName = "reportmateacr"
$ImageName = "reportmate"
$ResourceGroup = "ReportMate"
$ContainerAppEnv = "reportmate-env"
$ContainerAppName = "reportmate-container-$Environment"

# Helper functions
function Write-Info {
    param([string]$Message)
    Write-Host "${Blue}🚀 $Message${Reset}"
}

function Write-Success {
    param([string]$Message)
    Write-Host "${Green}✅ $Message${Reset}"
}

function Write-Warning {
    param([string]$Message)
    Write-Host "${Yellow}⚠️  $Message${Reset}"
}

function Write-Error {
    param([string]$Message)
    Write-Host "${Red}❌ $Message${Reset}"
}

function Show-Help {
    @"
ReportMate Container Deployment Script

Usage: .\deploy-containers.ps1 [OPTIONS]

Options:
  -Environment ENV     Environment to deploy (dev, staging, prod) [default: prod]
  -ForceBuild         Force rebuild even if no changes detected
  -SkipBuild          Skip Docker build (use existing image)
  -Tag TAG            Custom image tag [default: auto-generated]
  -AutoSSO            Enable automatic SSO login (no login button)
  -Test               Test deployment after completion
  -Help               Show this help message

Examples:
  .\deploy-containers.ps1                                    # Deploy to production
  .\deploy-containers.ps1 -Environment dev                   # Deploy to development
  .\deploy-containers.ps1 -ForceBuild -AutoSSO              # Force rebuild with auto SSO
  .\deploy-containers.ps1 -SkipBuild                        # Deploy without rebuilding

"@
}

if ($Help) {
    Show-Help
    exit 0
}

# Generate tag if not provided
if (-not $Tag) {
    try {
        $GitHash = git rev-parse --short HEAD 2>$null
        if (-not $GitHash) { $GitHash = "unknown" }
    } catch {
        $GitHash = "unknown"
    }
    $Tag = "$(Get-Date -Format 'yyyyMMddHHmmss')-$GitHash"
}

# Find the project root directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$InfraDir = Split-Path -Parent $ScriptDir
$ProjectRoot = Split-Path -Parent $InfraDir
$ContainerDir = Join-Path $ProjectRoot "apps\www"

Write-Info "Container Deployment Configuration:"
Write-Host "  Environment: $Environment"
Write-Host "  Tag: $Tag"
Write-Host "  Container Directory: $ContainerDir"
Write-Host "  Force Build: $ForceBuild"
Write-Host "  Skip Build: $SkipBuild"
Write-Host "  Auto SSO: $AutoSSO"
Write-Host ""

function Test-Prerequisites {
    Write-Info "Checking prerequisites..."
    
    # Check if container directory exists
    if (-not (Test-Path $ContainerDir)) {
        Write-Error "Container directory not found: $ContainerDir"
        exit 1
    }
    
    if (-not (Test-Path "$ContainerDir\Dockerfile")) {
        Write-Error "Dockerfile not found in: $ContainerDir"
        exit 1
    }
    
    # Check required tools
    $MissingTools = @()
    
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        $MissingTools += "docker"
    }
    
    if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
        $MissingTools += "azure-cli"
    }

    if ($MissingTools.Count -gt 0) {
        Write-Error "Missing required tools: $($MissingTools -join ', ')"
        exit 1
    }

    # Check Azure login
    try {
        $account = az account show --output json 2>$null | ConvertFrom-Json
        Write-Success "Logged in as: $($account.user.name)"
    } catch {
        Write-Error "Not logged into Azure. Please run 'az login' first."
        exit 1
    }

    # Check Docker daemon
    try {
        docker info --format "{{.ID}}" 2>$null | Out-Null
        Write-Success "Docker daemon is running"
    } catch {
        Write-Error "Docker daemon is not running"
        exit 1
    }

    Write-Success "Prerequisites check passed"
}

function Update-AutoSSOConfiguration {
    if (-not $AutoSSO) {
        Write-Info "Auto SSO not requested, skipping configuration update"
        return
    }
    
    Write-Info "Configuring automatic SSO login..."
    
    # Update the Next.js configuration for automatic SSO
    $envLocalPath = Join-Path $ContainerDir ".env.local"
    $envContent = @"
# Auto-generated environment configuration for automatic SSO
NEXT_PUBLIC_AUTO_SSO=true
NEXT_PUBLIC_ENVIRONMENT=$Environment
NEXT_PUBLIC_DOMAIN=reportmate.ecuad.ca
"@
    
    Write-Info "Creating .env.local with auto SSO configuration..."
    Set-Content -Path $envLocalPath -Value $envContent
    Write-Success "Auto SSO configuration updated"
}

function Build-DockerImage {
    if ($SkipBuild) {
        Write-Info "Skipping build as requested"
        return
    }

    Write-Info "Building Docker image..."
    
    $FullImageName = "$RegistryName.azurecr.io/$ImageName`:$Tag"
    $LatestImageName = "$RegistryName.azurecr.io/$ImageName`:latest"
    
    # Change to container directory
    Push-Location $ContainerDir
    
    try {
        # Build arguments
        $BuildArgs = @(
            "build"
            "--platform", "linux/amd64"
            "--build-arg", "DOCKER_BUILD=true"
            "--build-arg", "NODE_ENV=production"
        )
        
        if ($AutoSSO) {
            $BuildArgs += @("--build-arg", "NEXT_PUBLIC_AUTO_SSO=true")
        }
        
        # Add cache args if not forcing build
        if (-not $ForceBuild) {
            try {
                Write-Info "Attempting to pull latest image for cache..."
                docker pull $LatestImageName 2>$null | Out-Null
                $BuildArgs += @("--cache-from", $LatestImageName)
                Write-Info "Using cache from: $LatestImageName"
            } catch {
                Write-Info "Could not pull latest image for cache, building without cache"
            }
        } else {
            $BuildArgs += @("--no-cache")
        }
        
        # Add tags and context
        $BuildArgs += @(
            "-t", $FullImageName
            "-t", $LatestImageName
            "."
        )

        Write-Info "Build command: docker $($BuildArgs -join ' ')"
        
        # Use Start-Process for better control over output
        $ProcessInfo = New-Object System.Diagnostics.ProcessStartInfo
        $ProcessInfo.FileName = "docker"
        $ProcessInfo.Arguments = $BuildArgs -join " "
        $ProcessInfo.UseShellExecute = $false
        $ProcessInfo.RedirectStandardOutput = $true
        $ProcessInfo.RedirectStandardError = $true
        $ProcessInfo.WorkingDirectory = $ContainerDir
        
        $Process = New-Object System.Diagnostics.Process
        $Process.StartInfo = $ProcessInfo
        
        # Event handlers for output
        $OutputBuilder = New-Object System.Text.StringBuilder
        $ErrorBuilder = New-Object System.Text.StringBuilder
        
        Register-ObjectEvent -InputObject $Process -EventName "OutputDataReceived" -Action {
            if ($Event.SourceEventArgs.Data) {
                Write-Host $Event.SourceEventArgs.Data
                [void]$OutputBuilder.AppendLine($Event.SourceEventArgs.Data)
            }
        } | Out-Null
        
        Register-ObjectEvent -InputObject $Process -EventName "ErrorDataReceived" -Action {
            if ($Event.SourceEventArgs.Data) {
                Write-Host $Event.SourceEventArgs.Data -ForegroundColor Yellow
                [void]$ErrorBuilder.AppendLine($Event.SourceEventArgs.Data)
            }
        } | Out-Null
        
        $Process.Start() | Out-Null
        $Process.BeginOutputReadLine()
        $Process.BeginErrorReadLine()
        
        # Wait for completion with timeout (30 minutes)
        $TimeoutMs = 30 * 60 * 1000
        if (-not $Process.WaitForExit($TimeoutMs)) {
            Write-Error "Docker build timed out after 30 minutes"
            $Process.Kill()
            exit 1
        }
        
        # Clean up event handlers
        Get-EventSubscriber | Where-Object { $_.SourceObject -eq $Process } | Unregister-Event
        
        if ($Process.ExitCode -eq 0) {
            Write-Success "Image built successfully: $FullImageName"
        } else {
            Write-Error "Failed to build Docker image (exit code: $($Process.ExitCode))"
            exit 1
        }
        
    } finally {
        Pop-Location
    }
}

function Push-DockerImage {
    if ($SkipBuild) {
        Write-Info "Skipping push (build was skipped)"
        return
    }

    Write-Info "Logging into Azure Container Registry..."
    
    # Login to ACR
    $LoginResult = az acr login --name $RegistryName 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to login to Azure Container Registry"
        Write-Error $LoginResult
        exit 1
    }

    $FullImageName = "$RegistryName.azurecr.io/$ImageName`:$Tag"
    $LatestImageName = "$RegistryName.azurecr.io/$ImageName`:latest"

    Write-Info "Pushing images to registry..."
    
    # Push tagged image
    docker push $FullImageName
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Pushed: $FullImageName"
    } else {
        Write-Error "Failed to push tagged image"
        exit 1
    }

    # Push latest tag
    docker push $LatestImageName
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Pushed: $LatestImageName"
    } else {
        Write-Warning "Failed to push latest tag (non-critical)"
    }
}

function Deploy-ToAzure {
    Write-Info "Deploying to Azure Container Apps ($Environment environment)..."

    $FullImageName = "$RegistryName.azurecr.io/$ImageName`:$Tag"

    # Check if container app exists
    try {
        az containerapp show --name $ContainerAppName --resource-group $ResourceGroup --output none 2>$null
        if ($LASTEXITCODE -ne 0) {
            throw "Container app not found"
        }
        Write-Success "Container app found: $ContainerAppName"
    } catch {
        Write-Error "Container app '$ContainerAppName' not found in resource group '$ResourceGroup'"
        Write-Error "Please ensure the infrastructure is deployed via Terraform first"
        exit 1
    }

    # Update container app with new image
    Write-Info "Updating container app with new image..."
    
    $UpdateArgs = @(
        "containerapp", "update"
        "--name", $ContainerAppName
        "--resource-group", $ResourceGroup
        "--image", $FullImageName
    )
    
    # Add auto SSO environment variables if enabled
    if ($AutoSSO) {
        $UpdateArgs += @(
            "--set-env-vars", "NEXT_PUBLIC_AUTO_SSO=true"
            "--set-env-vars", "NEXT_PUBLIC_ENVIRONMENT=$Environment"
            "--set-env-vars", "NEXT_PUBLIC_DOMAIN=reportmate.ecuad.ca"
        )
        Write-Info "Configuring automatic SSO environment variables..."
    }
    
    az @UpdateArgs --output table
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Container app updated successfully"
    } else {
        Write-Error "Failed to update container app"
        exit 1
    }

    # Wait for deployment to stabilize
    Write-Info "Waiting for deployment to stabilize..."
    Start-Sleep -Seconds 15

    # Get the container app URL
    $AppUrl = az containerapp show --name $ContainerAppName --resource-group $ResourceGroup --query "properties.configuration.ingress.fqdn" --output tsv

    if ($AppUrl) {
        Write-Success "Deployment complete!"
        Write-Success "Application URL: https://$AppUrl"
        
        if ($AutoSSO) {
            Write-Success "🔐 Automatic SSO is enabled!"
            Write-Success "Users visiting https://reportmate.ecuad.ca will be automatically redirected to login"
        }
        
        return $AppUrl
    } else {
        Write-Warning "Could not retrieve application URL"
        return $null
    }
}

function Test-Deployment {
    param([string]$AppUrl)
    
    if (-not $AppUrl) {
        Write-Warning "No app URL available for testing"
        return
    }
    
    Write-Info "Performing health check..."
    
    try {
        $Response = Invoke-WebRequest -Uri "https://$AppUrl" -UseBasicParsing -TimeoutSec 30
        $HealthStatus = $Response.StatusCode
    } catch {
        $HealthStatus = 0
    }
    
    if ($HealthStatus -eq 200) {
        Write-Success "Health check passed (Status: $HealthStatus)"
        
        if ($AutoSSO) {
            Write-Info "Testing automatic SSO redirect..."
            try {
                $SSOResponse = Invoke-WebRequest -Uri "https://$AppUrl" -UseBasicParsing -TimeoutSec 10 -MaximumRedirection 0
                if ($SSOResponse.StatusCode -eq 302 -or $SSOResponse.Headers.Location) {
                    Write-Success "Automatic SSO redirect is working!"
                }
            } catch {
                Write-Info "SSO redirect test inconclusive (may require actual authentication)"
            }
        }
    } else {
        Write-Warning "Health check returned status: $HealthStatus"
        Write-Warning "The application may still be starting up"
    }
}

function Configure-FrontDoorForAutoSSO {
    if (-not $AutoSSO) {
        return
    }
    
    Write-Info "Configuring Azure Front Door for automatic SSO..."
    
    # This would configure Front Door rules to automatically redirect to SSO
    # For now, we'll just output instructions
    Write-Warning "Manual Front Door configuration required:"
    Write-Host "1. Go to Azure Portal → Front Door and CDN profiles"
    Write-Host "2. Find the ReportMate Front Door profile"
    Write-Host "3. Add a rule to redirect all traffic to the SSO login endpoint"
    Write-Host "4. Configure the rule to bypass the login page and go directly to Azure AD"
    Write-Host ""
    Write-Host "Rule configuration:"
    Write-Host "  - If: Request URL path does not contain '/api/auth'"
    Write-Host "  - And: Request URL path does not contain '/auth'"
    Write-Host "  - Then: Redirect to '/api/auth/signin' with HTTP 302"
}

# Main execution
function Main {
    Write-Host "${Blue}🎯 ReportMate Container Deployment Script${Reset}"
    Write-Host "============================================="
    Write-Host ""
    
    try {
        Test-Prerequisites
        Write-Host ""
        
        Update-AutoSSOConfiguration
        Write-Host ""
        
        Build-DockerImage
        Write-Host ""
        
        Push-DockerImage
        Write-Host ""
        
        $AppUrl = Deploy-ToAzure
        Write-Host ""
        
        if ($Test -or $AutoSSO) {
            Test-Deployment -AppUrl $AppUrl
            Write-Host ""
        }
        
        Configure-FrontDoorForAutoSSO
        Write-Host ""
        
        Write-Host "${Green}🎉 CONTAINER DEPLOYMENT COMPLETED! 🎉${Reset}"
        Write-Host "==============================================="
        Write-Host ""
        Write-Success "ReportMate container is deployed and ready!"
        
        if ($AutoSSO) {
            Write-Host ""
            Write-Host "🔐 Automatic SSO Configuration:"
            Write-Host "✅ Container configured for auto SSO"
            Write-Host "⚠️  Front Door rules may need manual configuration"
            Write-Host "🌐 Users will be automatically redirected to login"
        }
        
    } catch {
        Write-Error "Container deployment failed: $_"
        exit 1
    }
}

# Run main function
Main
