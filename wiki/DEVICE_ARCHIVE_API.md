# Device Archive API

## Overview

ReportMate supports archiving devices via the REST API. Archived devices are soft-deleted - they remain in the database with all historical data intact but are hidden from all bulk endpoints by default.

## API Endpoints

### Archive a Device

```
PATCH /api/device/{serial_number}/archive
```

**Authentication Required:**
- `X-API-PASSPHRASE` header (for scripts/automation)
- `X-MS-CLIENT-PRINCIPAL-ID` header (for Azure Managed Identity)

**Response:**
```json
{
  "success": true,
  "message": "Device {serial_number} has been archived",
  "serialNumber": "{serial_number}",
  "archived": true,
  "timestamp": "2025-12-07T..."
}
```

### Unarchive a Device

```
PATCH /api/device/{serial_number}/unarchive
```

### View Archived Devices

By default, archived devices are excluded from bulk endpoints. To include them:

```
GET /api/devices?includeArchived=true
```

## What Happens When a Device is Archived

1. Device is hidden from all bulk endpoints (`/api/devices`, `/api/stats/*`, etc.)
2. Device data remains intact in database
3. New data submissions from archived devices are rejected at ingestion
4. Device can still be accessed directly via `/api/device/{serial}` 
5. Device can be unarchived at any time to restore visibility

## Use Cases

- Decommissioned devices
- Devices being retired/replaced
- Test devices no longer needed
- Keeping historical data while hiding from active reports

---

## PowerShell Examples

### Query Devices by Location and Name Pattern

```powershell
$headers = @{ "X-API-PASSPHRASE" = "your-passphrase" }
$response = Invoke-RestMethod -Uri "https://reportmate-functions-api.blackdune-79551938.canadacentral.azurecontainerapps.io/api/devices" -Headers $headers
$devices = $response.devices

# Filter by location and name pattern
$filtered = $devices | Where-Object { 
    $_.location -eq 'A3080' -and $_.deviceName -like '*-LE*' 
}

# Display results
$filtered | Select-Object serialNumber, deviceName, location | Format-Table
```

### Bulk Archive Multiple Devices

```powershell
$headers = @{ "X-API-PASSPHRASE" = "your-passphrase" }
$serials = @("SERIAL1", "SERIAL2", "SERIAL3")

$success = 0
$failed = 0

foreach ($serial in $serials) {
    try {
        $result = Invoke-RestMethod `
            -Uri "https://reportmate-functions-api.blackdune-79551938.canadacentral.azurecontainerapps.io/api/device/$serial/archive" `
            -Method PATCH `
            -Headers $headers
        
        if ($result.success) {
            Write-Host "SUCCESS: $serial - $($result.message)" -ForegroundColor Green
            $success++
        } else {
            Write-Host "FAILED: $serial - $($result.detail)" -ForegroundColor Red
            $failed++
        }
    } catch {
        Write-Host "ERROR: $serial - $($_.Exception.Message)" -ForegroundColor Red
        $failed++
    }
}

Write-Host "`nTotal: $($serials.Count) | Success: $success | Failed: $failed"
```

### Bulk Unarchive Devices

```powershell
$headers = @{ "X-API-PASSPHRASE" = "your-passphrase" }
$serials = @("SERIAL1", "SERIAL2", "SERIAL3")

foreach ($serial in $serials) {
    $result = Invoke-RestMethod `
        -Uri "https://reportmate-functions-api.blackdune-79551938.canadacentral.azurecontainerapps.io/api/device/$serial/unarchive" `
        -Method PATCH `
        -Headers $headers
    Write-Host "$serial - $($result.message)"
}
```

---

## Archive Operation Log: December 7, 2025

**Purpose:** Archive 20 A3080 location devices with `-LE` suffix (Studio Lab loaner equipment)

**Devices Archived:**

| Serial | Device Name |
|--------|-------------|
| 53FFFF3 | Studio Lab 01-LE |
| 53GCFF3 | Studio Lab 02-LE |
| 53J4FF3 | Studio Lab 03-LE |
| 53HCFF3 | Studio Lab 04-LE |
| 53FDFF3 | Studio Lab 05-LE |
| 53H4FF3 | Studio Lab 06-LE |
| 53GBFF3 | Studio Lab 07-LE |
| 53FCFF3 | Studio Lab 08-LE |
| 53H6FF3 | Studio Lab 09-LE |
| 53G9FF3 | Studio Lab 10-LE |
| 53G4FF3 | Studio Lab 12-LE |
| 53HFFF3 | Studio Lab 13-LE |
| 53G6FF3 | Studio Lab 14-LE |
| 53H5FF3 | Studio Lab 15-LE |
| 53G7FF3 | Studio Lab 16-LE |
| 53H7FF3 | Studio Lab 17-LE |
| 53H8FF3 | Studio Lab 18-LE |
| 53H9FF3 | Studio Lab 19-LE |
| 53G5FF3 | Studio Lab 20-LE |
| 53HBFF3 | Studio Lab Instructor-LE |

**Command Used:**
```powershell
$headers = @{ "X-API-PASSPHRASE" = "XmZ8Kp3NwQ7YtR9vC2LzH6FgDj4BlMnE" }
$serials = @(
    "53FCFF3", "53FDFF3", "53FFFF3", "53G4FF3", "53G5FF3", 
    "53G6FF3", "53G7FF3", "53G9FF3", "53GBFF3", "53GCFF3", 
    "53H4FF3", "53H5FF3", "53H6FF3", "53H7FF3", "53H8FF3", 
    "53H9FF3", "53HBFF3", "53HCFF3", "53HFFF3", "53J4FF3"
)

foreach ($serial in $serials) {
    $result = Invoke-RestMethod `
        -Uri "https://reportmate-functions-api.blackdune-79551938.canadacentral.azurecontainerapps.io/api/device/$serial/archive" `
        -Method PATCH `
        -Headers $headers
    Write-Host "$serial - $($result.message)"
}
```

**Result:** 20/20 devices archived successfully

**Verification:**
- Total device count dropped from 363 to 343
- A3080 devices with `-LE` suffix no longer appear in `/api/devices` response
