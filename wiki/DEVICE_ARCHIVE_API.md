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
$response = Invoke-RestMethod -Uri "https://<api-host>/api/devices" -Headers $headers
$devices = $response.devices

# Filter by location and name pattern
$filtered = $devices | Where-Object { 
    $_.location -eq 'EXAMPLE-ROOM' -and $_.deviceName -like '*-LE*' 
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
            -Uri "https://<api-host>/api/device/$serial/archive" `
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
        -Uri "https://<api-host>/api/device/$serial/unarchive" `
        -Method PATCH `
        -Headers $headers
    Write-Host "$serial - $($result.message)"
}
```

---

## Archive Operation Log: December 7, 2025

**Purpose:** Archive a batch of loaner devices from one location, identified by a name suffix

**Devices Archived:**

| Serial | Device Name |
|--------|-------------|
| EXAMPLE001 | Example Lab 01 |
| EXAMPLE002 | Example Lab 02 |
| EXAMPLE003 | Example Lab 03 |
| EXAMPLE004 | Example Lab 04 |
| EXAMPLE005 | Example Lab 05 |
| EXAMPLE006 | Example Lab 06 |
| EXAMPLE007 | Example Lab 07 |
| EXAMPLE008 | Example Lab 08 |
| EXAMPLE009 | Example Lab 09 |
| EXAMPLE010 | Example Lab 10 |
| EXAMPLE011 | Example Lab 11 |
| EXAMPLE012 | Example Lab 12 |
| EXAMPLE013 | Example Lab 13 |
| EXAMPLE014 | Example Lab 14 |
| EXAMPLE015 | Example Lab 15 |
| EXAMPLE016 | Example Lab 16 |
| EXAMPLE017 | Example Lab 17 |
| EXAMPLE018 | Example Lab 18 |
| EXAMPLE019 | Example Lab 19 |
| EXAMPLE020 | Example Lab 20 |

**Command Used:**
```powershell
$headers = @{ "X-API-PASSPHRASE" = "$REPORTMATE_CLIENT_PASSPHRASE" }
$serials = @(
    "EXAMPLE001",
    "EXAMPLE002",
    "EXAMPLE003",
    "EXAMPLE004",
    "EXAMPLE005",
    "EXAMPLE006",
    "EXAMPLE007",
    "EXAMPLE008",
    "EXAMPLE009",
    "EXAMPLE010",
    "EXAMPLE011",
    "EXAMPLE012",
    "EXAMPLE013",
    "EXAMPLE014",
    "EXAMPLE015",
    "EXAMPLE016",
    "EXAMPLE017",
    "EXAMPLE018",
    "EXAMPLE019",
    "EXAMPLE020"
)

foreach ($serial in $serials) {
    $result = Invoke-RestMethod `
        -Uri "https://<api-host>/api/device/$serial/archive" `
        -Method PATCH `
        -Headers $headers
    Write-Host "$serial - $($result.message)"
}
```

**Result:** 20/20 devices archived successfully

**Verification:**
- Total device count dropped from 363 to 343
- Devices at that location with the `-LE` suffix no longer appear in `/api/devices` response
