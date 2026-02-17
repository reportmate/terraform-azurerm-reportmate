# Run database migration via API admin endpoint
$sql = Get-Content "c:\Users\rchristiansen\DevOps\ReportMate\infrastructure\azure\schemas\MANUAL_ADD_PLATFORM_COLUMN.sql" -Raw

$body = @{
    sql = $sql
} | ConvertTo-Json

$passphrase = $env:REPORTMATE_PASSPHRASE
if (-not $passphrase) {
    throw "REPORTMATE_PASSPHRASE environment variable not set. Export it before running this script."
}

$headers = @{
    "X-API-Passphrase" = $passphrase
    "Content-Type" = "application/json"
}

Write-Host "Running migration via API..." -ForegroundColor Cyan

try {
    $result = Invoke-RestMethod -Uri "https://reportmate-functions-api.blackdune-79551938.canadacentral.azurecontainerapps.io/api/admin/execute-sql" -Method Post -Headers $headers -Body $body
    
    Write-Host "✓ Migration executed successfully!" -ForegroundColor Green
    Write-Host "Result:" -ForegroundColor Yellow
    $result | ConvertTo-Json -Depth 5
    
} catch {
    Write-Host "✗ Migration failed:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    if ($_.ErrorDetails.Message) {
        Write-Host $_.ErrorDetails.Message -ForegroundColor Red
    }
    exit 1
}
