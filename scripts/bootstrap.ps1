#!/usr/bin/env pwsh
#Requires -Version 7.0

<#
.SYNOPSIS
    ReportMate Infrastructure Bootstrap Script
    
.DESCRIPTION
    Complete bootstrap setup for ReportMate infrastructure:
    - Terraform infrastructure provisioning
    - Database schema initialization
    - Function app deployment
    - Initial configuration and validation
    
    This script ensures everything is ready out-of-the-box for a new infrastructure deployment.
    
.PARAMETER Environment
    Environment to bootstrap (dev, staging, prod). Default: dev
    
.PARAMETER SkipTerraform
    Skip Terraform infrastructure deployment
    
.PARAMETER SkipDatabase
    Skip database schema initialization
    
.PARAMETER SkipFunctions
    Skip Azure Functions deployment
    
.PARAMETER AutoApprove
    Auto-approve Terraform deployment without prompts
    
.PARAMETER Validate
    Run validation checks after bootstrap
    
.EXAMPLE
    .\bootstrap.ps1
    # Complete bootstrap for dev environment
    
.EXAMPLE
    .\bootstrap.ps1 -Environment prod -AutoApprove
    # Bootstrap production with auto-approval
    
.EXAMPLE
    .\bootstrap.ps1 -SkipTerraform -Validate
    # Bootstrap database and functions only, then validate
#>

param(
    [Parameter(Mandatory = $false)]
    [ValidateSet("dev", "staging", "prod")]
    [string]$Environment = "dev",
    
    [Parameter(Mandatory = $false)]
    [switch]$SkipTerraform,
    
    [Parameter(Mandatory = $false)]
    [switch]$SkipDatabase,
    
    [Parameter(Mandatory = $false)]
    [switch]$SkipFunctions,
    
    [Parameter(Mandatory = $false)]
    [switch]$AutoApprove,
    
    [Parameter(Mandatory = $false)]
    [switch]$Validate
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

# Configuration
$CONFIG = @{
    ResourceGroup = "ReportMate"
    FunctionAppName = "reportmate-api"
    DatabaseServer = "reportmate-database"
    Regions = @{
        dev = "Canada Central"
        staging = "Canada Central"
        prod = "Canada Central"
    }
    TerraformDir = "$PSScriptRoot\.."
    FunctionsDir = "$PSScriptRoot\..\modules\functions"
}

# Colors and formatting
function Write-Header { param($Text) Write-Host "`n🚀 $Text" -ForegroundColor Magenta; Write-Host "═" * ($Text.Length + 4) -ForegroundColor Magenta }
function Write-Step { param($Text) Write-Host "`n🔄 $Text" -ForegroundColor Cyan }
function Write-Success { param($Text) Write-Host "✅ $Text" -ForegroundColor Green }
function Write-Warning { param($Text) Write-Host "⚠️  $Text" -ForegroundColor Yellow }
function Write-Error { param($Text) Write-Host "❌ $Text" -ForegroundColor Red }
function Write-Info { param($Text) Write-Host "ℹ️  $Text" -ForegroundColor Blue }

#region Prerequisites
function Test-Prerequisites {
    Write-Step "Checking Prerequisites"
    
    $missing = @()
    
    # Check Azure CLI
    try {
        $azVersion = & az version --output tsv --query '"azure-cli"' 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Azure CLI: $azVersion"
        } else {
            $missing += "Azure CLI"
        }
    } catch {
        $missing += "Azure CLI"
    }
    
    # Check Terraform
    try {
        $tfVersion = & terraform version -json 2>$null | ConvertFrom-Json
        if ($tfVersion.terraform_version) {
            Write-Success "Terraform: $($tfVersion.terraform_version)"
        } else {
            $missing += "Terraform"
        }
    } catch {
        $missing += "Terraform"
    }
    
    # Check PowerShell version
    if ($PSVersionTable.PSVersion.Major -ge 7) {
        Write-Success "PowerShell: $($PSVersionTable.PSVersion)"
    } else {
        $missing += "PowerShell 7+"
    }
    
    # Check Azure login
    try {
        $account = & az account show --output json 2>$null | ConvertFrom-Json
        if ($account.user.name) {
            Write-Success "Azure Login: $($account.user.name)"
        } else {
            $missing += "Azure Login (run 'az login')"
        }
    } catch {
        $missing += "Azure Login (run 'az login')"
    }
    
    if ($missing.Count -gt 0) {
        Write-Error "Missing prerequisites:"
        $missing | ForEach-Object { Write-Error "  • $_" }
        throw "Prerequisites not met"
    }
    
    Write-Success "All prerequisites satisfied"
}
#endregion

#region Terraform Infrastructure
function Deploy-TerraformInfrastructure {
    if ($SkipTerraform) {
        Write-Warning "Skipping Terraform deployment"
        return
    }
    
    Write-Step "Deploying Terraform Infrastructure"
    
    try {
        Push-Location $CONFIG.TerraformDir
        
        # Check if terraform.tfvars exists
        if (-not (Test-Path "terraform.tfvars")) {
            if (Test-Path "terraform.tfvars.example") {
                Write-Info "Creating terraform.tfvars from example"
                Copy-Item "terraform.tfvars.example" "terraform.tfvars"
                Write-Warning "Please review and update terraform.tfvars before continuing"
                Write-Info "Press Enter when ready to continue..."
                if (-not $AutoApprove) { Read-Host }
            } else {
                throw "terraform.tfvars not found and no example available"
            }
        }
        
        # Initialize Terraform
        Write-Info "Initializing Terraform..."
        & terraform init
        if ($LASTEXITCODE -ne 0) { throw "Terraform init failed" }
        
        # Plan deployment
        Write-Info "Planning Terraform deployment..."
        if ($AutoApprove) {
            & terraform plan -out=tfplan
        } else {
            & terraform plan -out=tfplan
            Write-Info "Review the plan above. Press Enter to continue with apply..."
            Read-Host
        }
        if ($LASTEXITCODE -ne 0) { throw "Terraform plan failed" }
        
        # Apply deployment
        Write-Info "Applying Terraform deployment..."
        if ($AutoApprove) {
            & terraform apply -auto-approve tfplan
        } else {
            & terraform apply tfplan
        }
        if ($LASTEXITCODE -ne 0) { throw "Terraform apply failed" }
        
        Write-Success "Terraform infrastructure deployed successfully"
        
    } catch {
        Write-Error "Terraform deployment failed: $_"
        throw
    } finally {
        Pop-Location
    }
}
#endregion

#region Database Schema
function Initialize-DatabaseSchema {
    if ($SkipDatabase) {
        Write-Warning "Skipping database initialization"
        return
    }
    
    Write-Step "Initializing Database Schema"
    
    try {
        # Wait for database to be ready
        Write-Info "Waiting for database to be ready..."
        $maxAttempts = 12
        $attempt = 0
        
        do {
            $attempt++
            try {
                # Try to connect to database
                $connectionTest = & az postgres flexible-server execute --name $CONFIG.DatabaseServer --admin-user reportmate --admin-password "2sSWbVxyqjXp9WUpeMmzRaC" --database-name reportmate --querytext "SELECT 1;" --output table 2>$null
                if ($LASTEXITCODE -eq 0) {
                    Write-Success "Database is ready"
                    break
                }
            } catch {
                # Continue waiting
            }
            
            if ($attempt -lt $maxAttempts) {
                Write-Info "Database not ready, waiting 30 seconds... (attempt $attempt/$maxAttempts)"
                Start-Sleep -Seconds 30
            }
        } while ($attempt -lt $maxAttempts)
        
        if ($attempt -ge $maxAttempts) {
            throw "Database did not become ready within timeout"
        }
        
        # Initialize schema using API endpoint
        Write-Info "Initializing database schema via API..."
        
        $maxRetries = 5
        $retry = 0
        
        do {
            $retry++
            try {
                $response = Invoke-WebRequest -Uri "https://$($CONFIG.FunctionAppName).azurewebsites.net/api/init-db?init=true" -Method GET -UseBasicParsing -TimeoutSec 120
                
                if ($response.StatusCode -eq 200) {
                    $result = $response.Content | ConvertFrom-Json
                    Write-Success "Database schema initialized successfully"
                    Write-Info "Tables created: $($result.tables_created -join ', ')"
                    break
                } else {
                    throw "API returned status $($response.StatusCode)"
                }
            } catch {
                if ($retry -lt $maxRetries) {
                    Write-Warning "Schema initialization attempt $retry failed: $_"
                    Write-Info "Retrying in 30 seconds..."
                    Start-Sleep -Seconds 30
                } else {
                    throw "Schema initialization failed after $maxRetries attempts: $_"
                }
            }
        } while ($retry -lt $maxRetries)
        
        # Verify schema
        Write-Info "Verifying database schema..."
        
        $expectedTables = @(
            'devices', 'events',
            'applications', 'displays', 'hardware', 'installs', 'inventory',
            'management', 'network', 'printers', 'profiles', 'security', 'system'
        )
        
        foreach ($table in $expectedTables) {
            $tableCheck = & az postgres flexible-server execute --name $CONFIG.DatabaseServer --admin-user reportmate --admin-password "2sSWbVxyqjXp9WUpeMmzRaC" --database-name reportmate --querytext "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = '$table';" --output tsv 2>$null
            
            if ($tableCheck -and $tableCheck.Trim() -eq "1") {
                Write-Success "Table '$table' verified"
            } else {
                Write-Warning "Table '$table' not found or verification failed"
            }
        }
        
    } catch {
        Write-Error "Database schema initialization failed: $_"
        throw
    }
}
#endregion

#region Azure Functions
function Deploy-AzureFunctions {
    if ($SkipFunctions) {
        Write-Warning "Skipping Azure Functions deployment"
        return
    }
    
    Write-Step "Deploying Azure Functions"
    
    try {
        Push-Location $CONFIG.FunctionsDir
        
        # Check if function app exists
        $functionApp = & az functionapp show --name $CONFIG.FunctionAppName --resource-group $CONFIG.ResourceGroup --output json 2>$null
        
        if (-not $functionApp) {
            Write-Warning "Function app not found - should be created by Terraform"
            return
        }
        
        # Deploy functions
        Write-Info "Deploying function code..."
        
        # Package and deploy
        if (Test-Path "requirements.txt") {
            Write-Info "Installing Python dependencies..."
            & pip install -r requirements.txt --target ./.python_packages/lib/site-packages
        }
        
        # Deploy using Azure CLI
        & az functionapp deployment source config-zip --name $CONFIG.FunctionAppName --resource-group $CONFIG.ResourceGroup --src "function-app.zip" 2>$null
        
        # Alternative: Use direct deployment
        Write-Info "Deploying functions via direct method..."
        & func azure functionapp publish $CONFIG.FunctionAppName --python
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Azure Functions deployed successfully"
        } else {
            Write-Warning "Function deployment may have issues - continuing..."
        }
        
        # Wait for functions to be ready
        Write-Info "Waiting for functions to initialize..."
        Start-Sleep -Seconds 60
        
        # Test function endpoints
        $endpoints = @("/api/health", "/api/devices", "/api/events")
        foreach ($endpoint in $endpoints) {
            try {
                $testUrl = "https://$($CONFIG.FunctionAppName).azurewebsites.net$endpoint"
                $response = Invoke-WebRequest -Uri $testUrl -Method GET -UseBasicParsing -TimeoutSec 30
                Write-Success "Function $endpoint responding (status: $($response.StatusCode))"
            } catch {
                Write-Warning "Function $endpoint test failed: $_"
            }
        }
        
    } catch {
        Write-Error "Azure Functions deployment failed: $_"
        throw
    } finally {
        Pop-Location
    }
}
#endregion

#region Configuration
function Set-InitialConfiguration {
    Write-Step "Setting Initial Configuration"
    
    try {
        # Set function app settings
        Write-Info "Configuring function app settings..."
        
        $settings = @(
            "DATABASE_URL=postgresql://reportmate:2sSWbVxyqjXp9WUpeMmzRaC@$($CONFIG.DatabaseServer).postgres.database.azure.com:5432/reportmate?sslmode=require"
            "ENVIRONMENT=$Environment"
            "LOG_LEVEL=INFO"
        )
        
        foreach ($setting in $settings) {
            $settingParts = $setting -split "=", 2
            & az functionapp config appsettings set --name $CONFIG.FunctionAppName --resource-group $CONFIG.ResourceGroup --settings "$($settingParts[0])=$($settingParts[1])" --output none
        }
        
        Write-Success "Function app configured"
        
        # Create initial API key (if needed)
        Write-Info "Setting up API authentication..."
        # Add API key configuration here if needed
        
        Write-Success "Initial configuration completed"
        
    } catch {
        Write-Error "Configuration failed: $_"
        throw
    }
}
#endregion

#region Validation
function Invoke-ValidationChecks {
    if (-not $Validate) {
        return
    }
    
    Write-Step "Running Validation Checks"
    
    try {
        # Run the canonical check script
        $checkScript = "$PSScriptRoot\check.ps1"
        if (Test-Path $checkScript) {
            Write-Info "Running comprehensive health check..."
            & $checkScript -Environment $Environment -DetailedOutput
            
            if ($LASTEXITCODE -eq 0) {
                Write-Success "All validation checks passed"
            } else {
                Write-Warning "Some validation checks failed - review output above"
            }
        } else {
            Write-Warning "Check script not found at $checkScript"
        }
        
    } catch {
        Write-Error "Validation checks failed: $_"
        throw
    }
}
#endregion

#region Cleanup Old Scripts
function Remove-LegacyScripts {
    Write-Step "Cleaning Up Legacy Scripts"
    
    $legacyScripts = @(
        "$PSScriptRoot\..\..\scripts\*.js",
        "$PSScriptRoot\..\..\scripts\*.py",
        "$PSScriptRoot\..\..\*.js",
        "$PSScriptRoot\..\..\*.py",
        "$PSScriptRoot\..\..\apps\www\check-*.js",
        "$PSScriptRoot\..\..\apps\www\analyze-*.js",
        "$PSScriptRoot\..\..\apps\www\fix-*.js"
    )
    
    $removedCount = 0
    
    foreach ($pattern in $legacyScripts) {
        $files = Get-ChildItem $pattern -ErrorAction SilentlyContinue
        foreach ($file in $files) {
            # Skip if it's our new canonical scripts
            if ($file.Name -in @("check.ps1", "bootstrap.ps1")) {
                continue
            }
            
            try {
                Write-Info "Removing legacy script: $($file.Name)"
                Remove-Item $file.FullName -Force
                $removedCount++
            } catch {
                Write-Warning "Could not remove $($file.Name): $_"
            }
        }
    }
    
    if ($removedCount -gt 0) {
        Write-Success "Removed $removedCount legacy scripts"
    } else {
        Write-Info "No legacy scripts found to remove"
    }
}
#endregion

#region Main Execution
function Main {
    Write-Header "ReportMate Infrastructure Bootstrap"
    Write-Info "Environment: $Environment"
    Write-Info "Skip Terraform: $SkipTerraform"
    Write-Info "Skip Database: $SkipDatabase"
    Write-Info "Skip Functions: $SkipFunctions"
    Write-Info "Auto Approve: $AutoApprove"
    Write-Info "Validate: $Validate"
    
    if (-not $AutoApprove) {
        Write-Warning "This will deploy complete ReportMate infrastructure to Azure"
        Write-Info "Press Enter to continue or Ctrl+C to abort..."
        Read-Host
    }
    
    try {
        # Step 1: Prerequisites
        Test-Prerequisites
        
        # Step 2: Terraform Infrastructure
        Deploy-TerraformInfrastructure
        
        # Step 3: Database Schema
        Initialize-DatabaseSchema
        
        # Step 4: Azure Functions
        Deploy-AzureFunctions
        
        # Step 5: Initial Configuration
        Set-InitialConfiguration
        
        # Step 6: Validation
        Invoke-ValidationChecks
        
        # Step 7: Cleanup
        Remove-LegacyScripts
        
        # Success
        Write-Header "Bootstrap Completed Successfully"
        Write-Success "ReportMate infrastructure is ready!"
        Write-Info ""
        Write-Info "🌐 API Endpoint: https://$($CONFIG.FunctionAppName).azurewebsites.net"
        Write-Info "🗄️  Database: $($CONFIG.DatabaseServer).postgres.database.azure.com"
        Write-Info "📊 Resource Group: $($CONFIG.ResourceGroup)"
        Write-Info ""
        Write-Info "Next Steps:"
        Write-Info "1. Test the Windows client: runner.exe test"
        Write-Info "2. View the web interface: https://reportmate-web.azurewebsites.net"
        Write-Info "3. Monitor with: .\check.ps1"
        
        return 0
        
    } catch {
        Write-Error "Bootstrap failed: $_"
        Write-Info ""
        Write-Info "🔧 Troubleshooting:"
        Write-Info "1. Check Azure login: az account show"
        Write-Info "2. Verify permissions: az role assignment list"
        Write-Info "3. Review logs: az monitor activity-log list"
        Write-Info "4. Run diagnostics: .\check.ps1"
        
        return 1
    }
}

# Execute main function
try {
    $exitCode = Main
    exit $exitCode
} catch {
    Write-Error "Bootstrap script failed: $_"
    exit 1
}
#endregion
