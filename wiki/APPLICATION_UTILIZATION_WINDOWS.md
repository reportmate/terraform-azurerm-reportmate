# Application Utilization Module - Windows Implementation

## Overview

The Application Utilization module tracks how installed applications are being used across devices in the fleet. This provides insights into software adoption, usage patterns, and helps with license management decisions.

**Key Principle**: We only track utilization for **installed applications** (from inventory), not system processes or random executables.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        APPLICATION UTILIZATION FLOW                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  COLLECTION (Windows Client)                                                │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  ApplicationUsageService.cs                                          │   │
│  │  ├── Reads Windows Event Logs (Security 4688/4689 or Kernel)        │   │
│  │  ├── Extracts process start/stop events                              │   │
│  │  ├── Builds usage sessions with duration calculation                 │   │
│  │  ├── Matches sessions to INSTALLED APPLICATIONS ONLY                 │   │
│  │  └── Outputs to applications.json → data.usage.activeSessions[]     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              ↓                                              │
│  TRANSMISSION                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  EventProcessor.cs                                                   │   │
│  │  └── Bundles applications.json into event.json payload              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              ↓                                              │
│  API (FastAPI Container)                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  main.py - /api/devices/applications/usage                          │   │
│  │  ├── Queries applications table JSONB                               │   │
│  │  ├── Filters sessions by installed applications (safeguard)         │   │
│  │  ├── Aggregates: totalHours, uniqueUsers, deviceCount per app       │   │
│  │  └── Returns fleet-wide utilization report                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              ↓                                              │
│  FRONTEND (Next.js)                                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  FleetApplicationsReport.tsx                                         │   │
│  │  ├── Fetches /api/devices/applications/usage                        │   │
│  │  ├── Displays utilization table with hours, users, devices          │   │
│  │  ├── Shows top users section                                         │   │
│  │  └── Period filtering (7d, 30d, 90d, All Time)                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Model

### Client-Side Output (applications.json)

```json
{
  "installedApplications": [
    {
      "name": "Docker Desktop",
      "version": "4.34.0",
      "installLocation": "C:\\Program Files\\Docker\\Docker",
      "publisher": "Docker Inc.",
      "installDate": "2024-11-15"
    }
  ],
  "usage": {
    "isCaptureEnabled": true,
    "captureMethod": "SecurityLog",
    "activeSessions": [
      {
        "name": "Docker Desktop",
        "path": "C:\\Program Files\\Docker\\Docker\\Docker Desktop.exe",
        "user": "DOMAIN\\username",
        "startTime": "2025-12-14T08:30:00Z",
        "endTime": "2025-12-14T17:45:00Z",
        "durationSeconds": 33300,
        "processId": 12345
      }
    ]
  }
}
```

### Database Storage (PostgreSQL)

```sql
-- applications table
CREATE TABLE applications (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(255) REFERENCES devices(serial_number),
    data JSONB,  -- Contains installedApplications[] and usage{}
    collected_at TIMESTAMP WITH TIME ZONE
);

-- Access patterns:
-- data->'installedApplications' -- Array of installed apps
-- data->'usage'->'activeSessions' -- Array of usage sessions
-- data->'usage'->>'isCaptureEnabled' -- Boolean flag
```

### API Response Structure

```json
{
  "success": true,
  "period": "30d",
  "cutoffDate": "2025-11-14T00:00:00Z",
  "summary": {
    "totalApplications": 45,
    "totalDevices": 120,
    "devicesWithUsageEnabled": 85,
    "totalUsageHours": 15420.5
  },
  "applications": [
    {
      "name": "Docker Desktop",
      "normalizedName": "docker desktop",
      "totalSeconds": 892800,
      "totalHours": 248.0,
      "uniqueUsers": 12,
      "deviceCount": 15,
      "devices": ["SERIAL1", "SERIAL2"],
      "version": "4.34.0"
    }
  ],
  "topUsers": [
    {
      "username": "jsmith",
      "totalSeconds": 432000,
      "totalHours": 120.0,
      "launchCount": 450,
      "appsUsed": 8,
      "devicesUsed": 2
    }
  ]
}
```

---

## Windows Client Implementation

### File: `clients/windows/src/Services/ApplicationUsageService.cs`

#### Key Methods

**1. CollectUsageDataAsync()**
- Entry point for usage collection
- Checks if audit logging is enabled
- Calls BuildSessionsFromEvents() to extract sessions

**2. BuildSessionsFromEvents()**
- Reads Windows Event Logs for process events
- Security Log: Events 4688 (Process Created) and 4689 (Process Exited)
- Kernel-Process/Operational: Events 1 (Start) and 2 (Stop)
- Calculates session duration from start/stop pairs
- **Critical Filter**: Only adds sessions that match installed applications

```csharp
// Key filtering logic in BuildSessionsFromEvents()
var matchedApp = installedApps.FirstOrDefault(app => MatchesApplication(session.Path, app));
if (matchedApp != null)
{
    session.Name = matchedApp.Name;  // Use installed app name
    sessions.Add(session);
}
// Sessions NOT matching installed apps are SKIPPED
```

**3. MatchesApplication()**
- Matches a process path to an installed application
- Uses install location prefix matching
- Example: `C:\Program Files\Docker\Docker\Docker Desktop.exe` matches app with `InstallLocation: C:\Program Files\Docker\Docker`

**4. IsAuditLoggingEnabled()**
- Checks if Windows process auditing is configured
- Required for Security Log method to work

#### Session Object Properties

| Property | Type | Description |
|----------|------|-------------|
| `name` | string | Application name (from installed apps) |
| `path` | string | Full executable path |
| `user` | string | User who ran the process (DOMAIN\user) |
| `startTime` | DateTime | When process started |
| `endTime` | DateTime? | When process ended (null if still running) |
| `durationSeconds` | long | Calculated duration |
| `processId` | int | Windows Process ID |

---

## API Implementation

### File: `infrastructure/modules/api/main.py`

### Endpoint: `GET /api/devices/applications/usage`

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `period` | string | "30d" | Time period: 7d, 30d, 90d, all |
| `include_archived` | bool | false | Include archived devices |

#### SQL Query Logic

The API uses CTEs (Common Table Expressions) to:

1. **installed_apps CTE** - Extract unique app names from each device's `installedApplications` JSONB array
2. **sessions_extracted CTE** - Extract usage sessions from `activeSessions` JSONB array
3. **Filter sessions** - Only include sessions where app name exists in installed_apps for that device
4. **Aggregate** - Sum durations, count users, count devices per application

```sql
WITH installed_apps AS (
    -- Get installed applications from each device
    SELECT DISTINCT 
        d.serial_number,
        app_item->>'name' as app_name
    FROM applications a
    INNER JOIN devices d ON a.device_id = d.serial_number,
    LATERAL jsonb_array_elements(a.data->'installedApplications') as app_item
),
sessions_extracted AS (
    SELECT 
        d.serial_number,
        session->>'name' as app_name,
        session->>'user' as username,
        (session->>'durationSeconds')::numeric as duration_seconds
    FROM applications a
    INNER JOIN devices d ON a.device_id = d.serial_number,
    LATERAL jsonb_array_elements(a.data->'usage'->'activeSessions') as session
    WHERE (a.data->'usage'->>'isCaptureEnabled')::boolean = true
)
SELECT 
    se.app_name,
    SUM(se.duration_seconds) as total_seconds,
    COUNT(DISTINCT se.username) as unique_users,
    COUNT(DISTINCT se.serial_number) as device_count
FROM sessions_extracted se
-- CRITICAL: Only include sessions for installed applications
INNER JOIN installed_apps ia 
    ON se.serial_number = ia.serial_number 
    AND se.app_name = ia.app_name
GROUP BY se.app_name
ORDER BY total_seconds DESC;
```

---

## Frontend Implementation

### File: `apps/www/src/components/reports/FleetApplicationsReport.tsx`

#### Features

1. **Data Table**
   - Application name
   - Total usage hours (formatted)
   - Unique users count
   - Device count
   - Version (from inventory)

2. **Top Users Section**
   - Username
   - Total hours
   - Apps used count
   - Devices used count

3. **Period Selector**
   - 7 days, 30 days, 90 days, All Time
   - Hidden on initial load, shown after data loads

4. **Export Capabilities**
   - CSV export of utilization data

---

## Why We Filter to Installed Applications Only

### Problem
Process telemetry captures ALL executables that run on a device:
- System processes (TrustedInstaller.exe, svchost.exe)
- Background services (msedgewebview2.exe)
- Internal tools (runner.exe, managedreportsrunner.exe)
- Temporary/downloaded executables

### Solution
We only care about **software that IT deployed and manages**. By filtering to installed applications:
- Reports show actionable data (apps IT can manage)
- No noise from system processes
- Accurate license utilization tracking
- Clean, professional reports

### Two-Level Protection

1. **Client-side** (ApplicationUsageService.cs)
   - Only adds sessions that match installed apps
   - Prevents unnecessary data from being transmitted

2. **API-side** (main.py)
   - Filters by installed apps when querying
   - Safeguard for any legacy data in database

---

## Enabling Usage Collection on Windows

### Requirements

1. **Process Creation Auditing** must be enabled:
   ```
   Local Security Policy → Advanced Audit Policy Configuration 
   → Detailed Tracking → Audit Process Creation: Success
   ```

2. **Or** use Kernel-Process logging (less common)

### Verification

The client checks `IsAuditLoggingEnabled()` and sets:
```json
{
  "usage": {
    "isCaptureEnabled": true,  // or false if not enabled
    "captureMethod": "SecurityLog"  // or "KernelProcess" or "None"
  }
}
```

---

## Testing Commands

### Check API Response
```powershell
# Get fleet utilization data
curl -s "https://reportmate-functions-api.blackdune-79551938.canadacentral.azurecontainerapps.io/api/devices/applications/usage?period=30d" | ConvertFrom-Json

# Check a specific device's applications
curl -s "https://reportmate-functions-api.blackdune-79551938.canadacentral.azurecontainerapps.io/api/device/SERIALNUMBER" | ConvertFrom-Json | Select-Object -ExpandProperty applications
```

### Run Client Collection
```powershell
# Collect applications data only
sudo pwsh -c "& 'C:\Program Files\ReportMate\managedreportsrunner.exe' -vv --run-module applications"

# Transmit to API
sudo pwsh -c "& 'C:\Program Files\ReportMate\managedreportsrunner.exe' -vv --transmit-only"
```

### Check Local Cache
```powershell
# View collected applications data
Get-Content "C:\ProgramData\ManagedReports\cache\applications.json" | ConvertFrom-Json | ConvertTo-Json -Depth 10
```

---

## Key Files Reference

| Component | File | Purpose |
|-----------|------|---------|
| Client Service | `clients/windows/src/Services/ApplicationUsageService.cs` | Collects usage from Event Logs |
| Client Module | `clients/windows/src/Modules/ApplicationsModule.cs` | Orchestrates collection |
| API Endpoint | `infrastructure/modules/api/main.py` | Fleet utilization API |
| Frontend Report | `apps/www/src/components/reports/FleetApplicationsReport.tsx` | UI component |
| Frontend Hook | `apps/www/src/hooks/useFleetApplicationsReport.ts` | Data fetching |

---

## Changelog

### December 2025
- Added filtering to only track installed applications
- Implemented two-level protection (client + API)
- Added Period selector to fleet report
- Fixed version display using normalized app names
- Deployed to production (revision 108)
