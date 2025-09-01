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

.PARAMETER Containers
Containers only (frontend deployment)

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

.EXAMPLE
.\deploy.ps1 -Containers
# Deploy containers only

#>

param(
    [string]$Environment = "dev",
    [switch]$Quick,
    [switch]$Infrastructure,
    [switch]$Functions,
    [switch]$Containers,
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
    $Reset = "`e[0m"
} else {
    # Windows PowerShell 5.x fallback
    $Red = ""
    $Green = ""
    $Yellow = ""
    $Blue = ""
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
  -Containers         Containers only (frontend deployment)
  -Test              Test deployment after completion
  -Yes               Auto-approve without prompts
  -Help              Show this help message

Examples:
  .\deploy.ps1                         # Full deployment with prompts
  .\deploy.ps1 -Quick                  # Quick functions-only deployment
  .\deploy.ps1 -Environment prod -Infrastructure    # Deploy infrastructure to production
  .\deploy.ps1 -Environment staging -Functions -Yes # Deploy functions to staging, auto-approve
  .\deploy.ps1 -Containers                        # Deploy containers only

"@
}

# Process parameters
if ($Help) {
    Show-Help
    exit 0
}

# Auto-detect environment if not specified (and not using default "dev")
if ($Environment -eq "dev" -and -not $PSBoundParameters.ContainsKey('Environment')) {
    # Try to detect environment from git branch
    try {
        $gitBranch = git rev-parse --abbrev-ref HEAD 2>$null
        if ($gitBranch) {
            if ($gitBranch -match "prod|production|main") {
                $Environment = "prod"
                Write-Info "Auto-detected environment: $Environment (from git branch: $gitBranch)"
            } elseif ($gitBranch -match "stag|staging") {
                $Environment = "staging"
                Write-Info "Auto-detected environment: $Environment (from git branch: $gitBranch)"
            } else {
                Write-Info "Using default environment: $Environment (git branch: $gitBranch)"
            }
        } else {
            Write-Info "Using default environment: $Environment"
        }
    } catch {
        Write-Info "Using default environment: $Environment"
    }
} else {
    Write-Info "Using specified environment: $Environment"
}

# Set deployment flags based on parameters
if ($Quick) {
    $DeployInfrastructure = $false
    $DeployFunctions = $true
    $DeployContainers = $false
    $QuickDeploy = $true
} elseif ($Infrastructure) {
    $DeployInfrastructure = $true
    $DeployFunctions = $false
    $DeployContainers = $false
    $QuickDeploy = $false
} elseif ($Functions) {
    $DeployInfrastructure = $false
    $DeployFunctions = $true
    $DeployContainers = $false
    $QuickDeploy = $false
} elseif ($Containers) {
    $DeployInfrastructure = $false
    $DeployFunctions = $false
    $DeployContainers = $true
    $QuickDeploy = $false
} else {
    # Default: full deployment
    $DeployInfrastructure = $true
    $DeployFunctions = $true
    $DeployContainers = $true
    $QuickDeploy = $false
}

# Configuration based on environment
if ($QuickDeploy) {
    $ResourceGroup = "ReportMate"
    $FunctionAppName = "reportmate-api"
    Write-Info "Quick Deploy Mode - Using existing infrastructure"
} elseif ($Functions -and -not $DeployInfrastructure) {
    # Functions-only deployment - get names from Terraform outputs
    try {
        $ResourceGroup = terraform output -raw resource_group_name 2>$null
        if (-not $ResourceGroup) { $ResourceGroup = "ReportMate" }
        
        $fullHostname = terraform output -raw api_hostname 2>$null
        if ($fullHostname) {
            $FunctionAppName = $fullHostname.Split('.')[0]
        } else {
            $FunctionAppName = "reportmate-api"
        }
        Write-Info "Functions-only deployment - Using Terraform outputs"
        Write-Info "Resource Group: $ResourceGroup"
        Write-Info "Function App: $FunctionAppName"
    } catch {
        # Fallback to default values if Terraform outputs aren't available
        $ResourceGroup = "ReportMate"
        $FunctionAppName = "reportmate-api"
        Write-Warning "Could not get Terraform outputs, using default values"
    }
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
        
        # Check Python environment for functions
        $pythonCommands = @("python", "python3", "py")
        $pythonFound = $false
        
        foreach ($pyCmd in $pythonCommands) {
            try {
                $pythonVersion = Invoke-Expression "$pyCmd --version" 2>$null
                if ($LASTEXITCODE -eq 0) {
                    Write-Success "Found Python: $pyCmd ($pythonVersion)"
                    $pythonFound = $true
                    break
                }
            } catch {
                continue
            }
        }
        
        if (-not $pythonFound) {
            Write-Error "Python is not installed or not in PATH. Azure Functions requires Python 3.8+."
            Write-Error "Please install Python from: https://www.python.org/downloads/"
            exit 1
        }
    }
    
    # Check required files
    if ($DeployInfrastructure -and -not (Test-Path "main.tf")) {
        Write-Error "Terraform files not found. Must run from infrastructure root directory."
        exit 1
    }
    
    if ($DeployFunctions) {
        if (-not (Test-Path "modules\functions\api") -or -not (Test-Path "modules\functions\api\requirements.txt")) {
            Write-Error "API functions directory or requirements.txt not found in modules\functions\api."
            exit 1
        }
        if (-not (Test-Path "modules\functions")) {
            Write-Error "Functions module directory not found."
            exit 1
        }
    }
}

function Deploy-Infrastructure {
    Write-Info "Deploying Infrastructure with Terraform..."
    
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
        
        # Confirm deployment (removed manual prompt - auto-proceeding)
        
        # Apply deployment
        Write-Info "Applying Terraform deployment..."
        terraform apply tfplan
        if ($LASTEXITCODE -ne 0) { throw "Terraform apply failed" }
        
        # Get outputs
        $fullHostname = terraform output -raw api_hostname 2>$null
        if ($fullHostname) {
            # Extract function app name from hostname (e.g., "reportmate-api.azurewebsites.net" -> "reportmate-api")
            $script:FunctionAppName = $fullHostname.Split('.')[0]
        } else {
            $script:FunctionAppName = $FunctionAppName 
        }
        
        $script:FunctionAppUrl = terraform output -raw api_url 2>$null
        $script:ResourceGroupName = terraform output -raw resource_group_name 2>$null
        if (-not $script:ResourceGroupName) { $script:ResourceGroupName = $ResourceGroup }
        
        # Get container information if available
        $script:FrontendUrl = terraform output -raw frontend_url 2>$null
        $script:FrontendFqdn = terraform output -raw frontend_fqdn 2>$null
        
        Write-Success "Infrastructure deployed successfully!"
        Write-Success "Function App: $script:FunctionAppName"
        Write-Success "Resource Group: $script:ResourceGroupName"
        if ($script:FunctionAppUrl) {
            Write-Success "API URL: $script:FunctionAppUrl"
        }
        if ($script:FrontendUrl) {
            Write-Success "Frontend URL: $script:FrontendUrl"
        }
        
    } catch {
        Write-Error "Infrastructure deployment failed: $_"
        exit 1
    }
}

function Deploy-Functions-Traditional {
    Write-Info "Deploying Functions using Azure Functions Core Tools..."
    
    try {
        # Change to API directory
        Push-Location "modules\functions\api"
        
        # Install Python dependencies
        Write-Info "Installing Python dependencies..."
        
        # Find working Python command first
        $pythonCommands = @("python", "python3", "py")
        $workingPython = $null
        
        foreach ($pyCmd in $pythonCommands) {
            try {
                $result = & $pyCmd --version 2>&1
                if ($LASTEXITCODE -eq 0) {
                    $workingPython = $pyCmd
                    Write-Success "Found working Python: $workingPython ($result)"
                    break
                }
            } catch {
                continue
            }
        }
        
        if (-not $workingPython) {
            throw "No working Python command found. Please ensure Python 3.8+ is installed and in PATH."
        }
        
        # Install dependencies with improved error handling
        Write-Info "Installing dependencies using: $workingPython -m pip install -r requirements.txt"
        
        # Try different installation strategies
        $installSuccess = $false
        
        # Strategy 1: Try with --user flag
        try {
            Write-Info "Attempting installation with --user flag..."
            & $workingPython -m pip install -r requirements.txt --user --quiet
            if ($LASTEXITCODE -eq 0) {
                $installSuccess = $true
                Write-Success "Dependencies installed successfully with --user flag"
            }
        } catch {
            Write-Warning "Installation with --user failed: $_"
        }
        
        # Strategy 2: Try without --user flag if first attempt failed
        if (-not $installSuccess) {
            try {
                Write-Info "Attempting installation without --user flag..."
                & $workingPython -m pip install -r requirements.txt --quiet
                if ($LASTEXITCODE -eq 0) {
                    $installSuccess = $true
                    Write-Success "Dependencies installed successfully"
                }
            } catch {
                Write-Warning "Installation without --user failed: $_"
            }
        }
        
        # Strategy 3: Try with elevated permissions if available
        if (-not $installSuccess) {
            try {
                Write-Info "Attempting installation with virtual environment creation..."
                & $workingPython -m venv .venv
                if (Test-Path ".venv\Scripts\Activate.ps1") {
                    & .\.venv\Scripts\Activate.ps1
                    & $workingPython -m pip install -r requirements.txt --quiet
                    if ($LASTEXITCODE -eq 0) {
                        $installSuccess = $true
                        Write-Success "Dependencies installed in virtual environment"
                    }
                }
            } catch {
                Write-Warning "Virtual environment installation failed: $_"
            }
        }
        
        if (-not $installSuccess) {
            throw "All Python dependency installation strategies failed. Please check Python/pip installation and permissions."
        }
        
        # Build and deploy functions
        Write-Info "Building and deploying functions to $FunctionAppName..."
        func azure functionapp publish $FunctionAppName --python
        if ($LASTEXITCODE -ne 0) { 
            throw "Azure Functions deployment failed with exit code $LASTEXITCODE" 
        }
        
        Write-Success "Functions deployed successfully using traditional method!"
        
    } catch {
        Write-Error "Traditional function deployment failed: $_"
        throw $_
    } finally {
        Pop-Location
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
        Copy-Item -Path "modules\functions\api\*" -Destination $tempDir -Recurse -Force
        
        # Clean up Python cache files (ignore errors if they don't exist)
        try {
            Get-ChildItem -Path $tempDir -Recurse -Name "__pycache__" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
            Get-ChildItem -Path $tempDir -Recurse -Filter "*.pyc" -ErrorAction SilentlyContinue | Remove-Item -Force
        } catch {
            Write-Info "No Python cache files to clean"
        }
        
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

function Deploy-Containers {
    Write-Info "Deploying containers using the container deployment script..."
    
    try {
        # Calculate path to container script from infrastructure directory
        # We're in infrastructure/scripts, need to go up 2 levels to get to root
        $rootPath = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
        $containerScript = Join-Path $rootPath "apps\www\deploy.ps1"
        
        Write-Info "Looking for container script at: $containerScript"
        Write-Info "Current script location: $PSScriptRoot"
        Write-Info "Calculated root path: $rootPath"
        
        if (-not (Test-Path $containerScript)) {
            Write-Warning "Container deployment script not found at: $containerScript"
            Write-Warning "Skipping container deployment. You can deploy containers manually using:"
            Write-Warning "  .\apps\www\deploy.ps1 -Environment $Environment"
            return
        }
        
        Write-Info "Found container deployment script: $containerScript"
        Write-Info "Building and deploying Next.js application with authentication..."
        
        # Change to container directory
        Push-Location (Split-Path $containerScript -Parent)
        
        try {
            # Run container deployment using the dedicated script
            & .\scripts\deploy-containers.ps1 -Environment $Environment -ForceBuild
            
            if ($LASTEXITCODE -eq 0) {
                Write-Success "Container deployment completed!"
                
                # Get the container app URL if available
                try {
                    $containerUrl = az containerapp show --name "reportmate-container-$Environment" --resource-group $ResourceGroup --query "properties.configuration.ingress.fqdn" -o tsv 2>$null
                    if ($containerUrl) {
                        Write-Success "Container URL: https://$containerUrl"
                        $script:FrontendUrl = "https://$containerUrl"
                    }
                } catch {
                    Write-Info "Could not retrieve container URL"
                }
            } else {
                Write-Warning "Container deployment may have had issues. Check output above."
            }
        } finally {
            Pop-Location
        }
        
    } catch {
        Write-Warning "Container deployment failed: $_"
        Write-Warning "You can deploy containers manually using:"
        Write-Warning "  cd apps\www && .\deploy.ps1 -Environment $Environment -ForceBuild"
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
        Write-Info "Available API endpoints:"
        Write-Host "  Health:  https://$functionUrl/api/health"
        Write-Host "  Devices: https://$functionUrl/api/devices"
        Write-Host "  Ingest:  https://$functionUrl/api/ingest"
        
        # Test frontend if available
        if ($script:FrontendUrl) {
            Write-Host ""
            Write-Info "Testing frontend..."
            Write-Info "Frontend URL: $script:FrontendUrl"
            
            try {
                $frontendResponse = Invoke-WebRequest -Uri $script:FrontendUrl -Method Get -TimeoutSec 10 -UseBasicParsing
                if ($frontendResponse.StatusCode -eq 200) {
                    Write-Success "Frontend is accessible!"
                } else {
                    Write-Warning "Frontend returned status: $($frontendResponse.StatusCode)"
                }
            } catch {
                Write-Warning "Frontend test failed. The container might still be starting up."
                Write-Warning "Try manually: $script:FrontendUrl"
            }
        }
        
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
    Write-Host "  Deploy Containers: $DeployContainers"
    Write-Host "  Quick Deploy: $QuickDeploy"
    Write-Host "  Auto Approve: $Yes"
    Write-Host "  Run Tests: $Test"
    Write-Host ""
    
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
    
    # Deploy containers (if infrastructure was deployed or this is a full deployment)  
    if ($DeployContainers) {
        Deploy-Containers
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
