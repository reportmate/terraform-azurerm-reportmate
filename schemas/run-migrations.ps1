# Database Migration Scripts for ReportMate
# Run migrations to set up or update the PostgreSQL database

param(
    [string]$Server = "reportmate-database",
    [string]$Database = "reportmate", 
    [string]$Username = "reportmate",
    [string]$Password = $env:DB_PASSWORD,
    [string]$ResourceGroup = "ReportMate"
)

$ErrorActionPreference = "Stop"

# Validate required environment variable
if (-not $Password) {
    Write-Error "❌ DB_PASSWORD environment variable is not set. Please set it before running migrations."
    Write-Host "Example: `$env:DB_PASSWORD = 'your-password-here'; .\run-migrations.ps1" -ForegroundColor Yellow
    exit 1
}

Write-Host "🗄️  Running database migrations..." -ForegroundColor Green

# Test connection first
Write-Host "🔌 Testing database connection..." -ForegroundColor Yellow
try {
    $result = az postgres flexible-server execute --name $Server --admin-user $Username --admin-password $Password --database-name $Database --querytext "SELECT 1 as test;" --output json | ConvertFrom-Json
    Write-Host "✅ Database connection successful" -ForegroundColor Green
} catch {
    Write-Error "❌ Database connection failed: $_"
    exit 1
}

# Run migration files in order
$migrationFiles = @(
    "001-initial-migration.sql",
    "002-modules-migration.sql", 
    "003-indexes-migration.sql",
    "004-usage-history-migration.sql"
)

foreach ($migration in $migrationFiles) {
    $migrationPath = Join-Path $PSScriptRoot $migration
    
    if (Test-Path $migrationPath) {
        Write-Host "📄 Running migration: $migration..." -ForegroundColor Yellow
        
        try {
            $sql = Get-Content $migrationPath -Raw
            az postgres flexible-server execute --name $Server --admin-user $Username --admin-password $Password --database-name $Database --querytext $sql --output none
            Write-Host "✅ Migration $migration completed" -ForegroundColor Green
        } catch {
            Write-Error "❌ Migration $migration failed: $_"
            exit 1
        }
    } else {
        Write-Host "⚠️  Migration file not found: $migration" -ForegroundColor Yellow
    }
}

# Verify final state
Write-Host "🔍 Verifying database state..." -ForegroundColor Yellow
try {
    $deviceCount = az postgres flexible-server execute --name $Server --admin-user $Username --admin-password $Password --database-name $Database --querytext "SELECT COUNT(*) as count FROM devices;" --output json | ConvertFrom-Json
    $tableCount = az postgres flexible-server execute --name $Server --admin-user $Username --admin-password $Password --database-name $Database --querytext "SELECT COUNT(*) as count FROM information_schema.tables WHERE table_schema = 'public';" --output json | ConvertFrom-Json
    
    Write-Host "✅ Database ready:" -ForegroundColor Green
    Write-Host "   📊 Tables: $($tableCount[0].count)" -ForegroundColor Cyan
    Write-Host "   💻 Devices: $($deviceCount[0].count)" -ForegroundColor Cyan
} catch {
    Write-Warning "⚠️  Could not verify database state: $_"
}

Write-Host "🎉 Database migrations completed!" -ForegroundColor Green
