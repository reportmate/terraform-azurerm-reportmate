# Update Container - ReportMate
# Single script to update and redeploy container applications

param(
    [string]$ContainerName = "",
    [string]$ResourceGroup = "ReportMate",
    [switch]$Frontend = $false,
    [switch]$All = $false
)

$ErrorActionPreference = "Stop"

Write-Host "🐳 Updating ReportMate Containers..." -ForegroundColor Green

# Container configurations
$containers = @{
    "frontend" = @{
        "name" = "reportmate-frontend"
        "path" = "apps\www"
        "dockerfile" = "Dockerfile"
    }
}

function Update-Container {
    param($containerConfig, $containerType)
    
    $name = $containerConfig.name
    $path = $containerConfig.path
    $dockerfile = $containerConfig.dockerfile
    
    Write-Host "📦 Updating $containerType container ($name)..." -ForegroundColor Yellow
    
    # Build and push new image
    $imageName = "$name`:$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    $registryName = "reportmate" # Update with your ACR name
    
    try {
        # Build image
        Push-Location "$PSScriptRoot\..\..\$path"
        docker build -t $imageName -f $dockerfile .
        
        # Tag for registry
        docker tag $imageName "$registryName.azurecr.io/$imageName"
        
        # Push to registry
        az acr login --name $registryName
        docker push "$registryName.azurecr.io/$imageName"
        
        # Update container app
        az containerapp update --name $name --resource-group $ResourceGroup --image "$registryName.azurecr.io/$imageName"
        
        Write-Host "✅ $containerType container updated successfully" -ForegroundColor Green
        
    } catch {
        Write-Error "❌ Failed to update $containerType container: $_"
    } finally {
        Pop-Location
    }
}

# Determine which containers to update
if ($All) {
    foreach ($container in $containers.GetEnumerator()) {
        Update-Container $container.Value $container.Key
    }
} elseif ($Frontend) {
    Update-Container $containers.frontend "frontend"
} elseif ($ContainerName -and $containers.ContainsKey($ContainerName)) {
    Update-Container $containers[$ContainerName] $ContainerName
} else {
    Write-Host "🤔 Please specify which container to update:" -ForegroundColor Yellow
    Write-Host "   .\update-container.ps1 -Frontend" -ForegroundColor Cyan
    Write-Host "   .\update-container.ps1 -All" -ForegroundColor Cyan
    Write-Host "   .\update-container.ps1 -ContainerName frontend" -ForegroundColor Cyan
    exit 1
}

Write-Host "🎉 Container update completed!" -ForegroundColor Green
