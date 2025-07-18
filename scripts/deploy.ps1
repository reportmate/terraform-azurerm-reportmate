#!/usr/bin/env pwsh

<#
.SYNOPSIS
ReportMate REST API Unified Deployment Script

.DESCRIPTION
Supports both infrastructure deployment and quick function-only deployments.
Auto-detects environment and provides intelligent deployment options.
Cross-platform PowerShell script that works on Windows, macOS, and Linux.

.PARAMETER Environment
Environment to deploy (dev, staging, prod). Default: dev

.PARAMETER Quick
Quick deploy (functions only, use existing infrastructure)

.PARAMETER Infrastructure
Infrastructure only (Terraform deployment)

.PARAMETER Functions
Functions only (code deployment)

.PARAMETER Test
Test deployment after completion

.PARAMETER Yes
Auto-approve without prompts

.PARAMETER Help
Show help message

.EXAMPLE
.\deploy.ps1
# Full deployment with prompts

.EXAMPLE
.\deploy.ps1 -Quick
# Quick functions-only deployment

.EXAMPLE
.\deploy.ps1 -Environment prod -Infrastructure
# Deploy infrastructure to production

.EXAMPLE
.\deploy.ps1 -Environment staging -Functions -Yes
# Deploy functions to staging, auto-approve

#>

param(
    [string]$Environment = "dev",
    [switch]$Quick,
    [switch]$Infrastructure,
    [switch]$Functions,
    [switch]$Test,
    [switch]$Yes,
    [switch]$Help
)

# Set error action preference
$ErrorActionPreference = "Stop"

# Colors for output (cross-platform)
if ($PSVersionTable.PSVersion.Major -ge 7 -or $IsWindows -eq $false) {
    $Red = "`e[31m"
    $Green = "`e[32m"
    $Yellow = "`e[33m"
    $Blue = "`e[34m"
    $Cyan = "`e[36m"
    $Reset = "`e[0m"
} else {
    # Windows PowerShell 5.x fallback
    $Red = ""
    $Green = ""
    $Yellow = ""
    $Blue = ""
    $Cyan = ""
    $Reset = ""
}

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
ReportMate REST API Deployment Script

Usage: .\deploy.ps1 [OPTIONS]

Options:
  -Environment ENV     Environment to deploy (dev, staging, prod) [default: dev]
  -Quick              Quick deploy (functions only, use existing infrastructure)
  -Infrastructure     Infrastructure only (Terraform deployment)
  -Functions          Functions only (code deployment)
  -Test              Test deployment after completion
  -Yes               Auto-approve without prompts
  -Help              Show this help message

Examples:
  .\deploy.ps1                         # Full deployment with prompts
  .\deploy.ps1 -Quick                  # Quick functions-only deployment
  .\deploy.ps1 -Environment prod -Infrastructure    # Deploy infrastructure to production
  .\deploy.ps1 -Environment staging -Functions -Yes # Deploy functions to staging, auto-approve

"@
}

# Process parameters
if ($Help) {
    Show-Help
    exit 0
}

# Set deployment flags based on parameters
if ($Quick) {
    $DeployInfrastructure = $false
    $DeployFunctions = $true
    $QuickDeploy = $true
} elseif ($Infrastructure) {
    $DeployInfrastructure = $true
    $DeployFunctions = $false
    $QuickDeploy = $false
} elseif ($Functions) {
    $DeployInfrastructure = $false
    $DeployFunctions = $true
    $QuickDeploy = $false
} else {
    # Default: full deployment
    $DeployInfrastructure = $true
    $DeployFunctions = $true
    $QuickDeploy = $false
}

# Configuration based on environment
if ($QuickDeploy) {
    $ResourceGroup = "ReportMate"
    $FunctionAppName = "reportmate-api"
    Write-Info "Quick Deploy Mode - Using existing infrastructure"
} else {
    $ResourceGroup = "reportmate-api-$Environment"
    $FunctionAppName = "reportmate-api-$Environment"
}

function Test-Prerequisites {
    Write-Info "Checking prerequisites..."
    
    # Check Azure CLI
    if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
        Write-Error "Azure CLI is not installed. Please install it first."
        exit 1
    }
    Write-Success "Azure CLI is installed"
    
    # Check Azure login
    try {
        $account = az account show --output json 2>$null | ConvertFrom-Json
        Write-Success "Logged in as: $($account.user.name)"
        Write-Success "Subscription: $($account.name)"
    } catch {
        Write-Error "Not logged in to Azure. Please run 'az login' first."
        exit 1
    }
    
    # Check Terraform if needed
    if ($DeployInfrastructure) {
        if (-not (Get-Command terraform -ErrorAction SilentlyContinue)) {
            Write-Error "Terraform is not installed. Please install it first."
            exit 1
        }
        Write-Success "Terraform is installed"
    }
    
    # Check Azure Functions Core Tools if needed
    if ($DeployFunctions -and -not $QuickDeploy) {
        if (-not (Get-Command func -ErrorAction SilentlyContinue)) {
            Write-Error "Azure Functions Core Tools is not installed."
            Write-Error "Please install from: https://docs.microsoft.com/en-us/azure/azure-functions/functions-run-local"
            exit 1
        }
        Write-Success "Azure Functions Core Tools is installed"
    }
    
    # Check required files
    if ($DeployInfrastructure -and -not (Test-Path "terraform")) {
        Write-Error "Terraform directory not found. Must run from infrastructure directory."
        exit 1
    }
    
    if ($DeployFunctions) {
        if (-not (Test-Path "functions") -or -not (Test-Path "requirements.txt")) {
            Write-Error "Functions directory or requirements.txt not found."
            exit 1
        }
        if (-not (Test-Path "modules")) {
            Write-Error "Modules directory not found."
            exit 1
        }
    }
}

function Deploy-Infrastructure {
    Write-Info "Deploying Infrastructure with Terraform..."
    
    Push-Location "terraform"
    try {
        # Check for terraform.tfvars
        if (-not (Test-Path "terraform.tfvars")) {
            Write-Warning "terraform.tfvars not found. Using default values."
            Write-Warning "Consider creating terraform.tfvars for customization."
        }
        
        # Initialize Terraform
        Write-Info "Initializing Terraform..."
        terraform init
        if ($LASTEXITCODE -ne 0) { throw "Terraform init failed" }
        
        # Plan deployment
        Write-Info "Planning Terraform deployment..."
        terraform plan -var="environment=$Environment" -out=tfplan
        if ($LASTEXITCODE -ne 0) { throw "Terraform plan failed" }
        
        # Confirm deployment
        if (-not $Yes) {
            $response = Read-Host "`n🤔 Do you want to continue with infrastructure deployment? (y/N)"
            if ($response -notmatch '^[Yy]$') {
                Write-Error "Infrastructure deployment cancelled"
                exit 1
            }
        }
        
        # Apply deployment
        Write-Info "Applying Terraform deployment..."
        terraform apply tfplan
        if ($LASTEXITCODE -ne 0) { throw "Terraform apply failed" }
        
        # Get outputs
        $script:FunctionAppName = terraform output -raw function_app_name 2>$null
        if (-not $script:FunctionAppName) { $script:FunctionAppName = $FunctionAppName }
        
        $script:FunctionAppUrl = terraform output -raw function_app_url 2>$null
        $script:ResourceGroupName = terraform output -raw resource_group_name 2>$null
        if (-not $script:ResourceGroupName) { $script:ResourceGroupName = $ResourceGroup }
        
        Write-Success "Infrastructure deployed successfully!"
        Write-Success "Function App: $script:FunctionAppName"
        Write-Success "Resource Group: $script:ResourceGroupName"
        if ($script:FunctionAppUrl) {
            Write-Success "Function App URL: $script:FunctionAppUrl"
        }
        
    } catch {
        Write-Error "Infrastructure deployment failed: $_"
        exit 1
    } finally {
        Pop-Location
    }
}

function Deploy-Functions-Traditional {
    Write-Info "Deploying Functions using Azure Functions Core Tools..."
    
    try {
        # Install Python dependencies
        Write-Info "Installing Python dependencies..."
        pip install -r requirements.txt
        if ($LASTEXITCODE -ne 0) { throw "pip install failed" }
        
        # Build and deploy functions
        Write-Info "Building and deploying functions..."
        func azure functionapp publish $FunctionAppName --python
        if ($LASTEXITCODE -ne 0) { throw "func publish failed" }
        
        Write-Success "Functions deployed using traditional method!"
        
    } catch {
        Write-Error "Traditional function deployment failed: $_"
        exit 1
    }
}

function Deploy-Functions-Quick {
    Write-Info "Quick deploying functions using ZIP deployment..."
    
    try {
        # Check if function app exists
        $appExists = az functionapp show --name $FunctionAppName --resource-group $ResourceGroup 2>$null
        if (-not $appExists) {
            Write-Error "Function app '$FunctionAppName' not found in resource group '$ResourceGroup'"
            Write-Host "Available function apps:"
            az functionapp list --resource-group $ResourceGroup --output table 2>$null
            exit 1
        }
        
        Write-Success "Function app found: $FunctionAppName"
        
        # Create deployment package
        Write-Info "Creating deployment package..."
        $tempDir = New-TemporaryFile | ForEach-Object { Remove-Item $_; New-Item -ItemType Directory -Path $_ }
        Write-Info "Using temp directory: $tempDir"
        
        # Copy files
        Copy-Item -Path "functions\*" -Destination $tempDir -Recurse -Force
        Copy-Item -Path "modules" -Destination $tempDir -Recurse -Force
        Copy-Item -Path "requirements.txt" -Destination $tempDir -Force
        
        # Clean up Python cache files
        Get-ChildItem -Path $tempDir -Recurse -Name "__pycache__" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
        Get-ChildItem -Path $tempDir -Recurse -Filter "*.pyc" -ErrorAction SilentlyContinue | Remove-Item -Force
        
        # Create ZIP
        $zipPath = "$env:TEMP\deployment.zip"
        if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
        
        Write-Info "Creating zip package..."
        Compress-Archive -Path "$tempDir\*" -DestinationPath $zipPath -Force
        
        # Deploy
        Write-Info "Deploying functions via ZIP..."
        az functionapp deployment source config-zip --resource-group $ResourceGroup --name $FunctionAppName --src $zipPath --timeout 300
        if ($LASTEXITCODE -ne 0) { throw "ZIP deployment failed" }
        
        # Clean up
        Remove-Item $tempDir -Recurse -Force
        Remove-Item $zipPath -Force
        
        Write-Success "Functions deployed via ZIP method!"
        
    } catch {
        Write-Error "Quick function deployment failed: $_"
        exit 1
    }
}

function Test-Deployment {
    Write-Info "Testing deployment..."
    
    try {
        # Get function app URL
        $functionUrl = az functionapp show --name $FunctionAppName --resource-group $ResourceGroup --query "defaultHostName" -o tsv 2>$null
        
        if (-not $functionUrl) {
            Write-Warning "Could not get function app URL. Skipping tests."
            return
        }
        
        Write-Info "Function App URL: https://$functionUrl"
        
        # Test health endpoint
        $healthUrl = "https://$functionUrl/api/health"
        Write-Info "Testing health endpoint: $healthUrl"
        
        # Wait for deployment to be ready
        Write-Info "Waiting for deployment to be ready..."
        Start-Sleep -Seconds 15
        
        try {
            $response = Invoke-RestMethod -Uri $healthUrl -Method Get -TimeoutSec 10
            Write-Success "Health check passed!"
            Write-Host "Response:"
            Write-Host ($response | ConvertTo-Json -Depth 3)
        } catch {
            Write-Warning "Health check failed. The API might still be starting up."
            Write-Warning "Try manually: $healthUrl"
        }
        
        Write-Host ""
        Write-Info "Available endpoints:"
        Write-Host "  Health:  https://$functionUrl/api/health"
        Write-Host "  Devices: https://$functionUrl/api/devices"
        Write-Host "  Ingest:  https://$functionUrl/api/ingest"
        
    } catch {
        Write-Warning "Test deployment failed: $_"
    }
}

# Main deployment function
function Main {
    Write-Host "${Blue}� ReportMate REST API Deployment Script${Reset}"
    Write-Host "========================================="
    Write-Host ""
    
    Write-Info "Configuration:"
    Write-Host "  Environment: $Environment"
    Write-Host "  Resource Group: $ResourceGroup"
    Write-Host "  Function App: $FunctionAppName"
    Write-Host "  Deploy Infrastructure: $DeployInfrastructure"
    Write-Host "  Deploy Functions: $DeployFunctions"
    Write-Host "  Quick Deploy: $QuickDeploy"
    Write-Host "  Auto Approve: $Yes"
    Write-Host "  Run Tests: $Test"
    Write-Host ""
    
    # Confirm deployment
    if (-not $Yes) {
        $response = Read-Host "🤔 Proceed with deployment? (y/N)"
        if ($response -notmatch '^[Yy]$') {
            Write-Error "Deployment cancelled"
            exit 1
        }
        Write-Host ""
    }
    
    # Check prerequisites
    Test-Prerequisites
    Write-Host ""
    
    # Deploy infrastructure
    if ($DeployInfrastructure) {
        Deploy-Infrastructure
        Write-Host ""
    }
    
    # Deploy functions
    if ($DeployFunctions) {
        if ($QuickDeploy) {
            Deploy-Functions-Quick
        } else {
            Deploy-Functions-Traditional
        }
        Write-Host ""
    }
    
    # Test deployment
    if ($Test -or $DeployFunctions) {
        Test-Deployment
        Write-Host ""
    }
    
    # Final summary
    Write-Host "${Green}🎉 DEPLOYMENT COMPLETED! 🎉${Reset}"
    Write-Host "=========================="
    Write-Host ""
    Write-Success "ReportMate REST API is deployed and ready!"
    Write-Host ""
    
    if ($DeployFunctions) {
        Write-Host "📋 Next steps:"
        Write-Host "1. Test the API endpoints"
        Write-Host "2. Update Windows client configuration"
        Write-Host "3. Update web application configuration"
        Write-Host "4. Set up monitoring and alerts"
    }
    
    if ($DeployInfrastructure) {
        Write-Host ""
        Write-Host "💡 Infrastructure deployed successfully!"
        Write-Host "   You can now use quick deployments with: .\deploy.ps1 -Quick"
    }
}

# Run main function
try {
    Main
} catch {
    Write-Error "Deployment failed: $_"
    exit 1
}
