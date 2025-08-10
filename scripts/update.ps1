# ReportMate Container Update Script (PowerShell)
# This script handles the complete process of updating the production container
# including building, pushing, deploying, and verifying the update
# Configuration is dynamically loaded from Terraform outputs and Azure resources

param(
    [string]$Action = "update"
)

# Set strict mode to catch errors early
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Global variables (loaded dynamically)
$script:RESOURCE_GROUP = ""
$script:CONTAINER_APP_NAME = ""
$script:ACR_NAME = ""
$script:IMAGE_NAME = ""  # Dynamically determined from current Container App image
$script:FRONTDOOR_PROFILE = ""
$script:FRONTDOOR_ENDPOINT = ""
$script:PRODUCTION_URL = ""
$script:CONTAINER_FQDN = ""

# Helper functions for colored output
function Write-Info($Message) {
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-Success($Message) {
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Warning($Message) {
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error($Message) {
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

function Confirm-Operation($Message) {
    $response = Read-Host "$Message (y/n)"
    if ($response -ne "y" -and $response -ne "Y") {
        Write-Info "Operation cancelled by user"
        exit 0
    }
}

function Import-Configuration {
    Write-Info "Loading configuration from Terraform and Azure..."
    
    # Check if we're in the infrastructure directory
    if (!(Test-Path "terraform.tfvars")) {
        Write-Error "Must run from infrastructure directory"
        exit 1
    }
    
    # Check if Terraform state exists
    try {
        $null = terraform output 2>$null
    } catch {
        Write-Error "Terraform state not found or not initialized. Run 'terraform init' and 'terraform apply' first"
        exit 1
    }
    
    # Load Terraform outputs
    try {
        $script:RESOURCE_GROUP = terraform output -raw resource_group_name 2>$null
        $script:PRODUCTION_URL = terraform output -raw frontend_url 2>$null
    } catch {
        Write-Error "Could not load Terraform outputs"
        exit 1
    }
    
    if ([string]::IsNullOrEmpty($script:RESOURCE_GROUP)) {
        Write-Error "Could not get resource group from Terraform outputs"
        exit 1
    }
    
    if ([string]::IsNullOrEmpty($script:PRODUCTION_URL)) {
        Write-Error "Could not get production URL from Terraform outputs"
        exit 1
    }
    
    Write-Success "Terraform configuration loaded:"
    Write-Info "  Resource Group: $script:RESOURCE_GROUP"
    Write-Info "  Production URL: $script:PRODUCTION_URL"
    
    # Discover Azure resources dynamically
    Write-Info "Discovering Azure resources..."
    
    # Find Container App
    try {
        $containerApps = az containerapp list --resource-group $script:RESOURCE_GROUP --query "[?contains(tags.Service, 'reportmate')].name" --output json | ConvertFrom-Json
        if ($containerApps -and $containerApps.Count -gt 0) {
            $script:CONTAINER_APP_NAME = $containerApps[0]
        } else {
            # Fallback: find any container app in the resource group
            $allContainerApps = az containerapp list --resource-group $script:RESOURCE_GROUP --query "[].name" --output json | ConvertFrom-Json
            if ($allContainerApps -and $allContainerApps.Count -gt 0) {
                $script:CONTAINER_APP_NAME = $allContainerApps[0]
            }
        }
    } catch {
        Write-Error "Error discovering Container App: $($_.Exception.Message)"
        exit 1
    }
    
    if ([string]::IsNullOrEmpty($script:CONTAINER_APP_NAME)) {
        Write-Error "Could not find Container App in resource group $script:RESOURCE_GROUP"
        exit 1
    }
    
    # Get Container App FQDN
    try {
        $script:CONTAINER_FQDN = az containerapp show --resource-group $script:RESOURCE_GROUP --name $script:CONTAINER_APP_NAME --query "properties.configuration.ingress.fqdn" --output tsv
    } catch {
        Write-Error "Could not get Container App FQDN"
        exit 1
    }
    
    # Find Azure Container Registry
    try {
        $acrList = az acr list --resource-group $script:RESOURCE_GROUP --query "[?contains(tags.Service, 'reportmate')].name" --output json | ConvertFrom-Json
        if ($acrList -and $acrList.Count -gt 0) {
            $script:ACR_NAME = $acrList[0]
        } else {
            # Fallback: find any ACR in the resource group
            $allAcrList = az acr list --resource-group $script:RESOURCE_GROUP --query "[].name" --output json | ConvertFrom-Json
            if ($allAcrList -and $allAcrList.Count -gt 0) {
                $script:ACR_NAME = $allAcrList[0]
            }
        }
    } catch {
        Write-Error "Error discovering Azure Container Registry: $($_.Exception.Message)"
        exit 1
    }
    
    if ([string]::IsNullOrEmpty($script:ACR_NAME)) {
        Write-Error "Could not find Azure Container Registry in resource group $script:RESOURCE_GROUP"
        exit 1
    }
    
    # Extract IMAGE_NAME from current Container App configuration
    try {
        $currentImage = az containerapp show --resource-group $script:RESOURCE_GROUP --name $script:CONTAINER_APP_NAME --query "properties.template.containers[0].image" --output tsv
        if (![string]::IsNullOrEmpty($currentImage)) {
            # Extract image name from full image path (e.g., "reportmateacr.azurecr.io/reportmate-web:latest" -> "reportmate-web")
            if ($currentImage -match '.*/([^:]*):.*') {
                $script:IMAGE_NAME = $matches[1]
            } elseif ($currentImage -match '^([^:]*):.*') {
                # Fallback: extract from simple image name (e.g., "reportmate-web:latest" -> "reportmate-web")
                $script:IMAGE_NAME = $matches[1]
            }
        }
    } catch {
        Write-Warning "Could not determine IMAGE_NAME from Container App: $($_.Exception.Message)"
    }
    
    if ([string]::IsNullOrEmpty($script:IMAGE_NAME)) {
        # Final fallback to standard naming convention
        $script:IMAGE_NAME = "reportmate-web"
        Write-Warning "Could not determine IMAGE_NAME from Container App, using fallback: $script:IMAGE_NAME"
    }
    
    # Find Front Door Profile and Endpoint
    try {
        $frontDoorProfiles = az afd profile list --resource-group $script:RESOURCE_GROUP --query "[?contains(tags.Service, 'reportmate')].name" --output json 2>$null | ConvertFrom-Json
        if ($frontDoorProfiles -and $frontDoorProfiles.Count -gt 0) {
            $script:FRONTDOOR_PROFILE = $frontDoorProfiles[0]
        } else {
            # Fallback: find any Front Door profile in the resource group
            $allFrontDoorProfiles = az afd profile list --resource-group $script:RESOURCE_GROUP --query "[].name" --output json 2>$null | ConvertFrom-Json
            if ($allFrontDoorProfiles -and $allFrontDoorProfiles.Count -gt 0) {
                $script:FRONTDOOR_PROFILE = $allFrontDoorProfiles[0]
            }
        }
        
        if (![string]::IsNullOrEmpty($script:FRONTDOOR_PROFILE)) {
            $frontDoorEndpoints = az afd endpoint list --resource-group $script:RESOURCE_GROUP --profile-name $script:FRONTDOOR_PROFILE --query "[].name" --output json 2>$null | ConvertFrom-Json
            if ($frontDoorEndpoints -and $frontDoorEndpoints.Count -gt 0) {
                $script:FRONTDOOR_ENDPOINT = $frontDoorEndpoints[0]
            }
        }
    } catch {
        Write-Warning "Error discovering Front Door resources: $($_.Exception.Message)"
    }
    
    # Log discovered configuration
    Write-Success "Azure resources discovered:"
    Write-Info "  Container App: $script:CONTAINER_APP_NAME"
    Write-Info "  Container FQDN: $script:CONTAINER_FQDN"
    Write-Info "  Container Registry: $script:ACR_NAME"
    Write-Info "  Image Name: $script:IMAGE_NAME"
    
    if (![string]::IsNullOrEmpty($script:FRONTDOOR_PROFILE)) {
        Write-Info "  Front Door Profile: $script:FRONTDOOR_PROFILE"
        Write-Info "  Front Door Endpoint: $script:FRONTDOOR_ENDPOINT"
    } else {
        Write-Warning "  Front Door not found - cache purging will be skipped"
    }
    
    Write-Success "Configuration loaded successfully"
}

function Test-Prerequisites {
    Write-Info "Checking prerequisites..."
    
    # Check if we're in the correct directory
    if (!(Test-Path "terraform.tfvars")) {
        Write-Error "Must run from infrastructure directory"
        exit 1
    }
    
    if (!(Test-Path "../apps/www/Dockerfile")) {
        Write-Error "Dockerfile not found at ../apps/www/Dockerfile"
        exit 1
    }
    
    # Check required tools
    $missingTools = @()
    
    try {
        $null = Get-Command az -ErrorAction Stop
    } catch {
        $missingTools += "Azure CLI"
    }
    
    try {
        $null = Get-Command docker -ErrorAction Stop
    } catch {
        $missingTools += "Docker"
    }
    
    try {
        $null = Get-Command terraform -ErrorAction Stop
    } catch {
        $missingTools += "Terraform"
    }
    
    if ($missingTools.Count -gt 0) {
        Write-Error "Missing required tools: $($missingTools -join ', ')"
        Write-Error "Please install the missing tools and try again"
        exit 1
    }
    
    # Check if logged into Azure
    try {
        $null = az account show 2>$null
    } catch {
        Write-Error "Not logged into Azure CLI. Run 'az login'"
        exit 1
    }
    
    Write-Success "All prerequisites met"
}

function New-Tag {
    $timestamp = Get-Date -Format "yyyyMMddHHmmss"
    try {
        $gitHash = git rev-parse --short HEAD 2>$null
        if (!$gitHash) { $gitHash = "nogit" }
    } catch {
        $gitHash = "nogit"
    }
    return "${timestamp}-${gitHash}"
}

function Build-AndPushImage($Tag) {
    Write-Info "Building and pushing container image with tag: $Tag"
    
    # Login to ACR
    Write-Info "Logging into Azure Container Registry..."
    az acr login --name $script:ACR_NAME
    
    # Build the image
    Write-Info "Building Docker image..."
    Push-Location "../apps/www"
    try {
        docker build -t "$($script:ACR_NAME).azurecr.io/$($script:IMAGE_NAME):$Tag" .
        if ($LASTEXITCODE -ne 0) {
            throw "Docker build failed"
        }
        
        # Push the image
        Write-Info "Pushing image to registry..."
        docker push "$($script:ACR_NAME).azurecr.io/$($script:IMAGE_NAME):$Tag"
        if ($LASTEXITCODE -ne 0) {
            throw "Docker push failed"
        }
    } finally {
        Pop-Location
    }
    
    Write-Success "Image built and pushed successfully"
}

function Update-ContainerApp($Tag) {
    Write-Info "Updating Container App to use new image..."
    
    # Update the container app
    az containerapp update --resource-group $script:RESOURCE_GROUP --name $script:CONTAINER_APP_NAME --image "$($script:ACR_NAME).azurecr.io/$($script:IMAGE_NAME):$Tag"
    
    if ($LASTEXITCODE -ne 0) {
        throw "Container App update failed"
    }
    
    # Wait for deployment to complete
    Write-Info "Waiting for deployment to complete..."
    $maxAttempts = 30
    $attempt = 0
    
    while ($attempt -lt $maxAttempts) {
        try {
            $status = az containerapp revision list --resource-group $script:RESOURCE_GROUP --name $script:CONTAINER_APP_NAME --query "reverse(sort_by([?active], &createdTime))[0].provisioningState" --output tsv
            
            if ($status -eq "Provisioned") {
                Write-Success "Container App deployment completed"
                break
            } elseif ($status -eq "Failed") {
                throw "Container App deployment failed"
            }
            
            Write-Info "Deployment status: $status (attempt $($attempt + 1)/$maxAttempts)"
            Start-Sleep -Seconds 10
            $attempt++
        } catch {
            Write-Warning "Error checking deployment status: $($_.Exception.Message)"
            Start-Sleep -Seconds 10
            $attempt++
        }
    }
    
    if ($attempt -eq $maxAttempts) {
        throw "Deployment timeout after $($maxAttempts * 10) seconds"
    }
}

function Test-ContainerHealth {
    Write-Info "Verifying container health..."
    
    # Test direct container access
    Write-Info "Testing direct container access..."
    try {
        $response = Invoke-RestMethod -Uri "https://$script:CONTAINER_FQDN/api/version" -Method Get -TimeoutSec 30
        if ($response.success -eq $true) {
            Write-Success "Direct container access working"
        } else {
            throw "API returned success=false"
        }
    } catch {
        Write-Error "Direct container access failed: $($_.Exception.Message)"
        return $false
    }
    
    # Get current revision info
    try {
        $revision = az containerapp revision list --resource-group $script:RESOURCE_GROUP --name $script:CONTAINER_APP_NAME --query "reverse(sort_by([?active], &createdTime))[0].name" --output tsv
        Write-Success "Active revision: $revision"
        Write-Success "Container FQDN: $script:CONTAINER_FQDN"
    } catch {
        Write-Warning "Could not get revision info: $($_.Exception.Message)"
    }
    
    return $true
}

function Clear-FrontDoorCache {
    if ([string]::IsNullOrEmpty($script:FRONTDOOR_PROFILE) -or [string]::IsNullOrEmpty($script:FRONTDOOR_ENDPOINT)) {
        Write-Warning "Front Door configuration not available - skipping cache purge"
        return
    }
    
    Write-Info "Purging Front Door cache..."
    
    try {
        # Purge all cached content
        az afd endpoint purge --resource-group $script:RESOURCE_GROUP --profile-name $script:FRONTDOOR_PROFILE --endpoint-name $script:FRONTDOOR_ENDPOINT --content-paths "/*"
        
        # Wait for cache purge to propagate
        Write-Info "Waiting for cache purge to propagate..."
        Start-Sleep -Seconds 30
        
        Write-Success "Front Door cache purged"
    } catch {
        Write-Warning "Cache purge failed: $($_.Exception.Message)"
    }
}

function Test-ProductionDeployment {
    Write-Info "Verifying production deployment..."
    
    $maxAttempts = 10
    $attempt = 0
    
    while ($attempt -lt $maxAttempts) {
        try {
            # Test version endpoint
            $versionResponse = Invoke-RestMethod -Uri "$script:PRODUCTION_URL/api/version" -Method Get -TimeoutSec 30
            
            # Test devices endpoint
            $devicesResponse = Invoke-RestMethod -Uri "$script:PRODUCTION_URL/api/devices" -Method Get -TimeoutSec 30
            
            if ($versionResponse.success -eq $true -and $devicesResponse.success -eq $true) {
                Write-Success "Production deployment verified successfully"
                
                # Show version info
                $versionInfo = if ($versionResponse.data.version) { $versionResponse.data.version } else { "unknown" }
                $buildId = if ($versionResponse.data.buildId) { $versionResponse.data.buildId } else { "unknown" }
                $buildTime = if ($versionResponse.data.buildTime) { $versionResponse.data.buildTime } else { "unknown" }
                
                Write-Success "Version: $versionInfo"
                Write-Success "Build ID: $buildId"
                Write-Success "Build Time: $buildTime"
                return $true
            }
        } catch {
            Write-Info "Production not ready yet (attempt $($attempt + 1)/$maxAttempts): $($_.Exception.Message)"
        }
        
        Start-Sleep -Seconds 30
        $attempt++
    }
    
    Write-Error "Production verification failed after $($maxAttempts * 30) seconds"
    return $false
}

function Show-Logs {
    Write-Info "Recent container logs:"
    try {
        az containerapp logs show --resource-group $script:RESOURCE_GROUP --name $script:CONTAINER_APP_NAME --follow false --tail 10
    } catch {
        Write-Warning "Could not retrieve logs: $($_.Exception.Message)"
    }
}

function Invoke-Rollback {
    Write-Warning "Rolling back to previous revision..."
    
    try {
        # Get the previous active revision
        $prevRevision = az containerapp revision list --resource-group $script:RESOURCE_GROUP --name $script:CONTAINER_APP_NAME --query "reverse(sort_by([?active], &createdTime))[1].name" --output tsv
        
        if ([string]::IsNullOrEmpty($prevRevision)) {
            Write-Error "No previous revision found for rollback"
            return $false
        }
        
        # Activate the previous revision
        az containerapp revision activate --resource-group $script:RESOURCE_GROUP --name $script:CONTAINER_APP_NAME --revision $prevRevision
        
        Write-Success "Rolled back to revision: $prevRevision"
        return $true
    } catch {
        Write-Error "Rollback failed: $($_.Exception.Message)"
        return $false
    }
}

function Invoke-Main {
    Write-Info "Starting ReportMate container update process..."
    
    # Check prerequisites and load configuration
    Test-Prerequisites
    Import-Configuration
    
    # Show current status
    Write-Info "Current production status:"
    if (!(Test-ContainerHealth)) {
        Write-Warning "Container health check failed"
    }
    
    # Confirm update
    Confirm-Operation "Do you want to proceed with the container update?"
    
    # Generate tag
    $tag = New-Tag
    Write-Info "Generated tag: $tag"
    
    try {
        # Build and push
        Build-AndPushImage $tag
        
        # Update container app
        Update-ContainerApp $tag
        
        # Verify container health
        if (!(Test-ContainerHealth)) {
            Write-Error "Container health verification failed"
            Confirm-Operation "Do you want to rollback?"
            Invoke-Rollback
            exit 1
        }
        
        # Purge cache
        Clear-FrontDoorCache
        
        # Verify production
        if (!(Test-ProductionDeployment)) {
            Write-Error "Production verification failed"
            Confirm-Operation "Do you want to rollback?"
            Invoke-Rollback
            exit 1
        }
        
        Write-Success "Container update completed successfully!"
        Write-Info "Production URL: $script:PRODUCTION_URL"
        
        # Show final logs
        Show-Logs
        
    } catch {
        Write-Error "Update failed: $($_.Exception.Message)"
        Write-Error $_.Exception.StackTrace
        exit 1
    }
}

# Handle command line arguments
switch ($Action.ToLower()) {
    "rollback" {
        Write-Info "Manual rollback requested"
        Test-Prerequisites
        Import-Configuration
        Invoke-Rollback
    }
    "logs" {
        Write-Info "Showing recent logs"
        Test-Prerequisites
        Import-Configuration
        Show-Logs
    }
    "status" {
        Write-Info "Checking current status"
        Test-Prerequisites
        Import-Configuration
        Test-ContainerHealth
    }
    "purge-cache" {
        Write-Info "Purging Front Door cache"
        Test-Prerequisites
        Import-Configuration
        Clear-FrontDoorCache
    }
    default {
        Invoke-Main
    }
}
