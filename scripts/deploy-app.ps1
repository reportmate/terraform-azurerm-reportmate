#!/usr/bin/env pwsh
<#
================================================================================
 DEPRECATED - USE CI/CD PIPELINE INSTEAD
================================================================================
 This script is DEPRECATED. Use the Azure DevOps pipeline instead:
 
   pipelines/reportmate-deploy-infra.yml
 
 The pipeline provides:
   - Terraform as single source of truth
   - Image tag variables passed to infrastructure
   - Proper CI/CD with approval gates
   - Audit trail of all deployments
   - Automatic Front Door cache purge
 
 This script is kept ONLY for emergency manual deployments.
================================================================================

.SYNOPSIS
    [DEPRECATED] Deploy the ReportMate Next.js frontend - Use CI/CD pipeline instead.

.DESCRIPTION
    DEPRECATED: This script is replaced by pipelines/reportmate-deploy-infra.yml
    
    Builds (optionally forced) and deploys the ReportMate frontend container, updates environment
    variables to keep build metadata accurate, and purges Azure Front Door so users always see the
    latest UI.

.PARAMETER Environment
    Target environment to deploy. Currently `prod` is supported.

.PARAMETER ForceBuild
    Rebuild the Docker image without using cache and force base image pulls.

.PARAMETER SkipBuild
    Skip Docker build/push and only update the container and metadata. When used without `-Tag`
    the script reuses the currently deployed tag.

.PARAMETER Tag
    Custom image tag. When omitted the script generates `<timestamp>-<git-hash>` from the apps/www
    submodule.

.PARAMETER AutoSSO
    Reserved for future use. Currently only surfaced in the summary output for completeness.

.PARAMETER PurgeOnly
    Only purge the Azure Front Door cache without building or deploying. Skips all other operations.

.EXAMPLE
    .\deploy-app.ps1
    # Standard deployment using Docker layer cache

.EXAMPLE
    .\deploy-app.ps1 -ForceBuild
    # Rebuild from scratch (no Docker cache) and deploy

.EXAMPLE
    .\deploy-app.ps1 -SkipBuild
    # Re-use the existing image but resync environment variables and purge CDN

.EXAMPLE
    .\deploy-app.ps1 -PurgeOnly
    # Only purge the Front Door cache, no build or deploy
#>

[CmdletBinding()]
param(
    [ValidateSet("prod")]
    [string]$Environment = "prod",
    [switch]$ForceBuild,
    [switch]$SkipBuild,
    [string]$Tag,
    [switch]$AutoSSO,
    [switch]$PurgeOnly
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

function Write-Section {
    param(
        [string]$Message,
        [ConsoleColor]$Color = [ConsoleColor]::Cyan
    )
    Write-Host "`n$Message" -ForegroundColor $Color
}

function Write-Info {
    param([string]$Message)
    Write-Host "   $Message" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "   $Message" -ForegroundColor Green
}

function Write-WarningLine {
    param([string]$Message)
    Write-Host "   $Message" -ForegroundColor Yellow
}

function Write-ErrorLine {
    param([string]$Message)
    Write-Host "   $Message" -ForegroundColor Red
}

# Resolve directory structure (script -> scripts -> azure -> infrastructure -> repo root -> apps/www)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$AzureDir = Split-Path -Parent $ScriptDir
$InfraDir = Split-Path -Parent $AzureDir
$RepoRoot = Split-Path -Parent $InfraDir
$FrontendDir = Join-Path $RepoRoot "apps/www"

if (-not (Test-Path $FrontendDir)) {
    throw "Unable to locate frontend directory at '$FrontendDir'."
}

$Environments = @{
    prod = @{
        ResourceGroup    = "ReportMate"
        ContainerApp     = "reportmate-web-app-prod"
        RegistryHost     = "reportmateacr.azurecr.io"
        ImageName        = "reportmate"
        Domain           = "reportmate.ecuad.ca"
        # Internal URL for server-side API calls (container-to-container within Azure)
        ApiBaseUrl       = "http://reportmate-functions-api"
        # External URL for client-side browser calls (WebSocket negotiate, etc.)
        PublicApiBaseUrl = "https://reportmate-functions-api.blackdune-79551938.canadacentral.azurecontainerapps.io"
        FrontDoorProfile = "reportmate-frontdoor"
        FrontDoorEndpoint= "reportmate-endpoint"
    }
}

if (-not $Environments.ContainsKey($Environment)) {
    throw "Unsupported environment '$Environment'."
}

$Config = $Environments[$Environment]
$RegistryHost = $Config.RegistryHost
$RegistryName = $RegistryHost.Split('.')[0]
$ImageName = $Config.ImageName

# === PurgeOnly fast path ===
if ($PurgeOnly) {
    Write-Section "🗑️  Purging Azure Front Door cache (purge-only mode)..." 'Yellow'
    
    az afd endpoint purge `
        --resource-group $Config.ResourceGroup `
        --profile-name $Config.FrontDoorProfile `
        --endpoint-name $Config.FrontDoorEndpoint `
        --content-paths "/*" `
        --domains $Config.Domain `
        --no-wait `
        --output none 2>&1 | Out-Null

    if ($LASTEXITCODE -eq 0) {
        Write-Success "Front Door cache purge triggered (async)"
        Write-Info "Domain: https://$($Config.Domain)"
    } else {
        Write-ErrorLine "Front Door purge command returned exit code $LASTEXITCODE"
    }
    exit $LASTEXITCODE
}

# Capture git hash from submodule first (before generating tag)
Push-Location $FrontendDir
try {
    $GitHash = git rev-parse --short HEAD 2>$null
} catch {
    $GitHash = $null
} finally {
    Pop-Location
}
if (-not $GitHash) { $GitHash = "unknown" }

if (-not $Tag) {
    $Timestamp = Get-Date -Format "yyyyMMddHHmmss"
    $Tag = "$Timestamp-$GitHash"
}

$BuildTime = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffZ")

# Extract API URLs from config
# - ApiBaseUrl = Internal URL for server-side calls (container-to-container)
# - PublicApiBaseUrl = External URL for client-side browser calls
$ApiBaseUrl = $Config.ApiBaseUrl
$PublicApiBaseUrl = $Config.PublicApiBaseUrl
if (-not $ApiBaseUrl) {
    throw "ApiBaseUrl is not configured for environment '$Environment'"
}
if (-not $PublicApiBaseUrl) {
    throw "PublicApiBaseUrl is not configured for environment '$Environment'"
}

Write-Section "Frontend Container Deployment Configuration:"
Write-Info "Environment: $Environment"
Write-Info "Target Container: $($Config.ContainerApp)"
Write-Info "Registry: $RegistryHost"
Write-Info "Image Name: $ImageName"
Write-Info "Tag: $Tag"
Write-Info "Force Build: $ForceBuild"
Write-Info "Skip Build: $SkipBuild"
Write-Info "Auto SSO: $AutoSSO"
Write-Info "Build Directory: $FrontendDir"
Write-Info "API Base URL (internal): $ApiBaseUrl"
Write-Info "API Base URL (public): $PublicApiBaseUrl"
Write-Info "SignalR Enabled: true (build-time)"

# === Prerequisite validation ===
Write-Section "Validating prerequisites..." 'Yellow'

# Ensure Docker is in PATH (common issue with fresh terminals)
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    $dockerBinPaths = @(
        "$env:ProgramFiles\Docker\Docker\resources\bin",
        "${env:ProgramFiles(x86)}\Docker\Docker\resources\bin",
        "$env:LOCALAPPDATA\Docker\Docker\resources\bin"
    )
    $foundDockerPath = $dockerBinPaths | Where-Object { Test-Path "$_\docker.exe" } | Select-Object -First 1
    if ($foundDockerPath) {
        Write-Info "Adding Docker to PATH: $foundDockerPath"
        $env:PATH = "$foundDockerPath;$env:PATH"
    }
}

# Check if Docker CLI is installed
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker CLI is not installed. Install Docker Desktop and retry."
}

# Check if Docker daemon is running, start it if not
$dockerRunning = $false
try {
    docker info 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        $dockerRunning = $true
    }
} catch {
    $dockerRunning = $false
}

if (-not $dockerRunning) {
    Write-WarningLine "Docker daemon not running. Attempting to start Docker Desktop..."
    
    # Try to find and start Docker Desktop
    $dockerDesktopPaths = @(
        "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe",
        "${env:ProgramFiles(x86)}\Docker\Docker\Docker Desktop.exe",
        "$env:LOCALAPPDATA\Docker\Docker Desktop.exe"
    )
    
    $dockerPath = $dockerDesktopPaths | Where-Object { Test-Path $_ } | Select-Object -First 1
    
    if ($dockerPath) {
        Write-Info "Starting Docker Desktop from: $dockerPath"
        Start-Process -FilePath $dockerPath -WindowStyle Minimized
        
        # Wait for Docker to start (up to 60 seconds)
        $maxWait = 60
        $waited = 0
        $interval = 3
        
        Write-Info "Waiting for Docker daemon to start (up to ${maxWait}s)..."
        while ($waited -lt $maxWait) {
            Start-Sleep -Seconds $interval
            $waited += $interval
            
            try {
                docker info 2>&1 | Out-Null
                if ($LASTEXITCODE -eq 0) {
                    $dockerRunning = $true
                    break
                }
            } catch {
                # Still waiting...
            }
            
            Write-Host "." -NoNewline
        }
        Write-Host ""
        
        if (-not $dockerRunning) {
            throw "Docker Desktop started but daemon didn't become available within ${maxWait}s. Please wait and retry."
        }
        
        Write-Success "Docker daemon started successfully"
    } else {
        throw "Docker Desktop not found. Install Docker Desktop and retry."
    }
} else {
    Write-Success "Docker daemon available"
}

try {
    $AccountInfo = az account show --output json | ConvertFrom-Json
    Write-Success "Azure CLI authenticated as $($AccountInfo.user.name)"
} catch {
    throw "Not logged into Azure CLI. Run 'az login' before deploying."
}

# Load current container metadata (used for env preservation and skip-build handling)
$ContainerJson = az containerapp show `
    --name $Config.ContainerApp `
    --resource-group $Config.ResourceGroup `
    --output json

if ($LASTEXITCODE -ne 0) {
    throw "Failed to fetch container app '$($Config.ContainerApp)'. Ensure it exists and you have permissions."
}

$ContainerInfo = $ContainerJson | ConvertFrom-Json
$CurrentImage = $ContainerInfo.properties.template.containers[0].image
$ExistingEnv = $ContainerInfo.properties.template.containers[0].env

if ($SkipBuild -and -not $Tag) {
    if ($CurrentImage -match ":(?<tag>[^:]+)$") {
        $Tag = $Matches['tag']
        Write-WarningLine "SkipBuild requested without tag - reusing deployed tag '$Tag'."
    } else {
        throw "Unable to infer currently deployed image tag; specify -Tag when using -SkipBuild."
    }
}

$FullImage = "$RegistryHost/$ImageName`:$Tag"
Write-Info "Resolved image reference: $FullImage"

# === Docker build & push ===
if (-not $SkipBuild) {
    Write-Section "Authenticating and building image..." 'Yellow'
    az acr login --name $RegistryName | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "ACR authentication failed for '$RegistryName'."
    }
    Write-Success "Authenticated to Azure Container Registry"

    Push-Location $FrontendDir
    try {
        $BuildArgs = @("build", "--platform", "linux/amd64",
            "--build-arg", "IMAGE_TAG=$Tag",
            "--build-arg", "BUILD_TIME=$BuildTime",
            "--build-arg", "BUILD_ID=$GitHash",
            "--build-arg", "ENABLE_SIGNALR=true",
            "--build-arg", "API_BASE_URL=$ApiBaseUrl",
            "--build-arg", "NEXT_PUBLIC_API_BASE_URL=$PublicApiBaseUrl"
        )

        if ($ForceBuild) {
            $BuildArgs = @("build", "--no-cache", "--pull", "--platform", "linux/amd64",
                "--build-arg", "IMAGE_TAG=$Tag",
                "--build-arg", "BUILD_TIME=$BuildTime",
                "--build-arg", "BUILD_ID=$GitHash",
                "--build-arg", "ENABLE_SIGNALR=true",
                "--build-arg", "API_BASE_URL=$ApiBaseUrl",
                "--build-arg", "NEXT_PUBLIC_API_BASE_URL=$PublicApiBaseUrl"
            )
        }

    $BuildArgs += @("-t", $FullImage, "-f", "Dockerfile", ".")

        Write-Info "Building Docker image (force build: $ForceBuild)..."
        docker @BuildArgs
        if ($LASTEXITCODE -ne 0) {
            throw "Docker build failed."
        }
        Write-Success "Image built successfully"

        Write-Info "Pushing image to $RegistryHost..."
        docker push $FullImage | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "Docker push failed."
        }
        Write-Success "Image pushed to registry"
    } finally {
        Pop-Location
    }
} else {
    Write-Section "Skipping Docker build/push per request" 'Yellow'
}

# === Environment variable reconciliation ===
Write-Section "Updating container configuration..." 'Yellow'

$EnvPairs = @()
$KeysToReplace = @(
    "CONTAINER_IMAGE_TAG",
    "BUILD_TIME",
    "BUILD_ID",
    "API_BASE_URL",
    "API_INTERNAL_SECRET",
    "NEXT_PUBLIC_API_BASE_URL",
    "NEXT_PUBLIC_VERSION",
    "NEXT_PUBLIC_BUILD_ID",
    "NEXT_PUBLIC_BUILD_TIME"
)

if ($ExistingEnv) {
    $envSeen = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
    foreach ($env in $ExistingEnv) {
        if (-not $env.name) { continue }
        if ($env.name -in $KeysToReplace) { continue }
        if (-not $envSeen.Add($env.name)) { continue }
        if ($env.secretRef) {
            $EnvPairs += "$($env.name)=secretref:$($env.secretRef)"
        } elseif ($null -ne $env.value) {
            $EnvPairs += "$($env.name)=$($env.value)"
        }
    }
}

$EnvPairs += "CONTAINER_IMAGE_TAG=$Tag"
$EnvPairs += "BUILD_TIME=$BuildTime"
$EnvPairs += "BUILD_ID=$GitHash"
$EnvPairs += "NEXT_PUBLIC_VERSION=$Tag"
$EnvPairs += "NEXT_PUBLIC_BUILD_ID=$GitHash"
$EnvPairs += "NEXT_PUBLIC_BUILD_TIME=$BuildTime"

# Set API URLs:
# - API_BASE_URL = Internal URL for server-side calls (container-to-container)
# - NEXT_PUBLIC_API_BASE_URL = External URL for client-side browser calls
$InternalApiUrl = $Config.ApiBaseUrl  # e.g., http://reportmate-functions-api
$PublicApiUrl = $Config.PublicApiBaseUrl  # e.g., https://...

if (-not $InternalApiUrl -and $ExistingEnv) {
    $InternalApiUrl = ($ExistingEnv | Where-Object { $_.name -eq "API_BASE_URL" } | Select-Object -First 1).value
}
if (-not $PublicApiUrl -and $ExistingEnv) {
    $PublicApiUrl = ($ExistingEnv | Where-Object { $_.name -eq "NEXT_PUBLIC_API_BASE_URL" } | Select-Object -First 1).value
}

if ($InternalApiUrl) {
    $EnvPairs += "API_BASE_URL=$InternalApiUrl"
}
if ($PublicApiUrl) {
    $EnvPairs += "NEXT_PUBLIC_API_BASE_URL=$PublicApiUrl"
}

# Set API_INTERNAL_SECRET for container-to-container authentication
# Fetch from Key Vault to ensure it matches what the API container expects
$KeyVaultName = "reportmate-keyvault"
$InternalSecret = $null

try {
    Write-Info "Fetching API_INTERNAL_SECRET from Key Vault..."
    $InternalSecret = az keyvault secret show --vault-name $KeyVaultName --name "api-internal-secret" --query "value" -o tsv 2>$null
    if ($LASTEXITCODE -eq 0 -and $InternalSecret) {
        Write-Success "API_INTERNAL_SECRET loaded from Key Vault"
    } else {
        $InternalSecret = $null
    }
} catch {
    Write-WarningLine "Key Vault lookup failed: $($_.Exception.Message)"
}

# Fallback chain: Key Vault -> Existing container value -> Hardcoded default
if (-not $InternalSecret) {
    $InternalSecret = ($ExistingEnv | Where-Object { $_.name -eq "API_INTERNAL_SECRET" } | Select-Object -First 1).value
    if ($InternalSecret) {
        Write-Info "Using existing API_INTERNAL_SECRET from container"
    }
}

if (-not $InternalSecret) {
    # Hardcoded fallback - matches the value set on the API container
    # This ensures deployments work even if Key Vault is unavailable
    $InternalSecret = "RmApi9IntSec7K3wP2vN8xF6HqL5bMnEz4Tj"
    Write-WarningLine "Using hardcoded API_INTERNAL_SECRET fallback"
}

$EnvPairs += "API_INTERNAL_SECRET=$InternalSecret"

$UpdateArgs = @(
    "containerapp", "update",
    "--name", $Config.ContainerApp,
    "--resource-group", $Config.ResourceGroup,
    "--image", $FullImage
)

if ($EnvPairs.Count -gt 0) {
    $UpdateArgs += "--set-env-vars"
    $UpdateArgs += $EnvPairs
}

az @UpdateArgs | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Container app update failed."
}
Write-Success "Container app updated with new image and metadata"

Write-Info "Waiting 30 seconds for the new revision to warm up..."
Start-Sleep -Seconds 30

try {
    $revisionJson = az containerapp revision list `
        --name $Config.ContainerApp `
        --resource-group $Config.ResourceGroup `
        -o json

    if ($LASTEXITCODE -eq 0 -and $revisionJson) {
        $revisions = $revisionJson | ConvertFrom-Json
        $ActiveRevision = $revisions |
            Where-Object { $_.properties.active -and $_.properties.trafficWeight -eq 100 } |
            Select-Object -First 1 -ExpandProperty name
        if ($ActiveRevision) {
            Write-Success "Active revision: $ActiveRevision"
        }
    } else {
        Write-WarningLine "Unable to determine active revision (exit code $LASTEXITCODE)."
    }
} catch {
    Write-WarningLine "Failed to read active revision: $($_.Exception.Message)"
}

# === CDN purge ===
Write-Section "🗑️  Purging Azure Front Door cache..." 'Yellow'

try {
    az afd endpoint purge `
        --resource-group $Config.ResourceGroup `
        --profile-name $Config.FrontDoorProfile `
        --endpoint-name $Config.FrontDoorEndpoint `
        --content-paths "/*" `
        --domains $Config.Domain `
        --no-wait `
        --output none 2>&1 | Out-Null

    if ($LASTEXITCODE -eq 0) {
        Write-Success "Front Door cache purge triggered (async)"
    } else {
        Write-WarningLine "Front Door purge command returned exit code $LASTEXITCODE"
    }
} catch {
    Write-WarningLine "Front Door purge failed: $($_.Exception.Message)"
}

# === Summary ===
Write-Section "════════════════ DEPLOYMENT SUMMARY ════════════════" 'Cyan'
Write-Success "Image: $FullImage"
Write-Success "Build Time (UTC): $BuildTime"
Write-Success "Build ID (git): $GitHash"
Write-Success "Container: $($Config.ContainerApp)"
Write-Success "Domain: https://$($Config.Domain)"
Write-Section "Next steps:" 'Green'
Write-Info "• Open https://$($Config.Domain) in an incognito window to verify"
Write-Info "• Visit /settings → check CONTAINER_IMAGE_TAG matches $Tag"
Write-Info "• If browser shows cached content, hard refresh (Ctrl+F5)"
Write-Section "Done." 'Green'
