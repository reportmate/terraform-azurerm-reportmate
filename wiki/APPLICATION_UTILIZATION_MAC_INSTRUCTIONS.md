# Application Utilization Module - Mac Implementation Guide

## Purpose

This document provides instructions for implementing the Application Utilization feature in the macOS ReportMate client. The goal is to track how installed applications are being used, matching the functionality already built for Windows.

---

## Requirements Summary

Build a service that:
1. Collects application usage data (which apps were run, by whom, for how long)
2. Matches usage sessions to **installed applications only** (critical requirement)
3. Outputs data in the same JSON structure as Windows for API compatibility

---

## Target Output Format

The macOS client must output usage data in this exact structure within `applications.json`:

```json
{
  "installedApplications": [
    {
      "name": "Docker Desktop",
      "version": "4.34.0",
      "installLocation": "/Applications/Docker.app",
      "publisher": "Docker Inc.",
      "installDate": "2024-11-15"
    }
  ],
  "usage": {
    "isCaptureEnabled": true,
    "captureMethod": "UnifiedLog",
    "activeSessions": [
      {
        "name": "Docker Desktop",
        "path": "/Applications/Docker.app/Contents/MacOS/Docker Desktop",
        "user": "jsmith",
        "startTime": "2025-12-14T08:30:00Z",
        "endTime": "2025-12-14T17:45:00Z",
        "durationSeconds": 33300,
        "processId": 12345
      }
    ]
  }
}
```

---

## Data Sources on macOS

### Option 1: Unified Log (Recommended)

macOS logs process activity to the Unified Logging system. Query with:

```bash
# Get process launch events
log show --predicate 'subsystem == "com.apple.launchd" AND eventMessage CONTAINS "spawn"' --last 24h

# Or use process subsystem
log show --predicate 'process == "launchd" AND eventMessage CONTAINS "Spawned"' --info --last 1d
```

### Option 2: BSM Audit (Basic Security Module)

If OpenBSM auditing is enabled:

```bash
# Check if auditing is enabled
sudo launchctl list | grep auditd

# Read audit logs
sudo praudit /var/audit/current
```

Audit events to capture:
- `AUE_EXECVE` - Process execution
- `AUE_EXIT` - Process exit

### Option 3: Endpoint Security Framework (ES)

For modern macOS (10.15+), the Endpoint Security framework provides real-time process events:
- `ES_EVENT_TYPE_NOTIFY_EXEC` - Process started
- `ES_EVENT_TYPE_NOTIFY_EXIT` - Process exited

**Note**: Requires Full Disk Access and special entitlements.

### Option 4: Activity Monitor / Top Polling

As a fallback, periodically poll running processes:

```bash
# Get running processes with user
ps aux

# Or use top in batch mode
top -l 1 -stats pid,command,user,time
```

**Limitation**: Polling misses short-lived processes and can't calculate accurate durations.

---

## Implementation Steps

### Step 1: Create ApplicationUsageService

Create a new service file (Swift or Objective-C depending on your client architecture):

```swift
// ApplicationUsageService.swift

class ApplicationUsageService {
    
    struct UsageSession {
        var name: String           // App name from installed apps
        var path: String           // Full executable path
        var user: String           // Username who ran it
        var startTime: Date
        var endTime: Date?
        var durationSeconds: Int64
        var processId: Int32
    }
    
    struct UsageData {
        var isCaptureEnabled: Bool
        var captureMethod: String
        var activeSessions: [UsageSession]
    }
    
    // Entry point
    func collectUsageData(installedApps: [InstalledApplication]) -> UsageData {
        // 1. Check if we can collect usage data
        guard let method = detectCaptureMethod() else {
            return UsageData(isCaptureEnabled: false, captureMethod: "None", activeSessions: [])
        }
        
        // 2. Collect process events
        let sessions = buildSessionsFromLogs(method: method, installedApps: installedApps)
        
        return UsageData(
            isCaptureEnabled: true,
            captureMethod: method,
            activeSessions: sessions
        )
    }
    
    // Detect which capture method is available
    private func detectCaptureMethod() -> String? {
        // Try Unified Log first
        if canAccessUnifiedLog() {
            return "UnifiedLog"
        }
        // Try BSM Audit
        if isAuditingEnabled() {
            return "BSMAudit"
        }
        // Fallback to polling
        return "ProcessPolling"
    }
    
    // Build sessions and match to installed apps
    private func buildSessionsFromLogs(method: String, installedApps: [InstalledApplication]) -> [UsageSession] {
        var sessions: [UsageSession] = []
        
        // Get raw process events based on method
        let rawEvents = getRawProcessEvents(method: method)
        
        // Match start/stop events to build sessions
        for event in rawEvents {
            var session = UsageSession(
                name: "",  // Will be set if matched
                path: event.path,
                user: event.user,
                startTime: event.startTime,
                endTime: event.endTime,
                durationSeconds: calculateDuration(start: event.startTime, end: event.endTime),
                processId: event.pid
            )
            
            // CRITICAL: Only add sessions that match installed applications
            if let matchedApp = matchToInstalledApp(path: event.path, installedApps: installedApps) {
                session.name = matchedApp.name
                sessions.append(session)
            }
            // Sessions that don't match are DISCARDED
        }
        
        return sessions
    }
    
    // Match process path to installed application
    private func matchToInstalledApp(path: String, installedApps: [InstalledApplication]) -> InstalledApplication? {
        for app in installedApps {
            // Check if process path starts with app's install location
            if let installLocation = app.installLocation {
                if path.hasPrefix(installLocation) {
                    return app
                }
            }
            // Also check bundle identifier if available
            if let bundleId = app.bundleIdentifier {
                if path.contains(bundleId) {
                    return app
                }
            }
        }
        return nil
    }
}
```

### Step 2: Unified Log Query Implementation

```swift
// Query Unified Log for process events
func queryUnifiedLog(since: Date) -> [ProcessEvent] {
    var events: [ProcessEvent] = []
    
    let dateFormatter = ISO8601DateFormatter()
    let sinceStr = dateFormatter.string(from: since)
    
    // Build log command
    let process = Process()
    process.executableURL = URL(fileURLWithPath: "/usr/bin/log")
    process.arguments = [
        "show",
        "--predicate", "subsystem == 'com.apple.launchd'",
        "--start", sinceStr,
        "--style", "json"
    ]
    
    let pipe = Pipe()
    process.standardOutput = pipe
    
    try? process.run()
    process.waitUntilExit()
    
    let data = pipe.fileHandleForReading.readDataToEndOfFile()
    // Parse JSON output and extract process events
    // ...
    
    return events
}
```

### Step 3: BSM Audit Implementation (Alternative)

```swift
// Parse BSM audit logs
func parseBSMAuditLogs(since: Date) -> [ProcessEvent] {
    var events: [ProcessEvent] = []
    
    // Run praudit to parse binary audit logs
    let process = Process()
    process.executableURL = URL(fileURLWithPath: "/usr/sbin/praudit")
    process.arguments = ["-x", "/var/audit/current"]  // XML output
    
    // Parse output for execve and exit events
    // ...
    
    return events
}
```

### Step 4: Integration with Applications Module

In your ApplicationsModule (or equivalent):

```swift
func collectApplicationsData() -> ApplicationsData {
    // 1. Collect installed applications (existing code)
    let installedApps = collectInstalledApplications()
    
    // 2. Collect usage data (NEW)
    let usageService = ApplicationUsageService()
    let usageData = usageService.collectUsageData(installedApps: installedApps)
    
    // 3. Build output
    return ApplicationsData(
        installedApplications: installedApps,
        usage: usageData
    )
}
```

---

## Critical Implementation Rules

### 1. Only Track Installed Applications

**DO NOT** send usage data for:
- System processes (launchd, kernel_task, etc.)
- Helper processes (mdworker, mds_stores, etc.)  
- Background daemons
- Processes not in your `installedApplications` list

The Windows implementation discards any session that doesn't match an installed app:

```csharp
// Windows implementation reference
var matchedApp = installedApps.FirstOrDefault(app => MatchesApplication(session.Path, app));
if (matchedApp != null)
{
    session.Name = matchedApp.Name;
    sessions.Add(session);
}
// No else - unmatched sessions are simply not added
```

### 2. Use App Name from Inventory

When a session matches an installed app, use the **installed application's name**, not the process name:

```swift
// CORRECT
session.name = matchedApp.name  // "Docker Desktop"

// WRONG
session.name = processName  // "Docker Desktop.app" or "com.docker.docker"
```

### 3. Calculate Duration Accurately

```swift
func calculateDuration(start: Date, end: Date?) -> Int64 {
    guard let endTime = end else {
        // Process still running - use current time
        return Int64(Date().timeIntervalSince(start))
    }
    return Int64(endTime.timeIntervalSince(start))
}
```

### 4. Normalize Usernames

Remove domain prefixes if present:

```swift
func normalizeUsername(_ username: String) -> String {
    // Handle domain\user format
    if let backslash = username.lastIndex(of: "\\") {
        return String(username[username.index(after: backslash)...])
    }
    return username
}
```

---

## macOS App Matching Strategy

### Path-Based Matching

Most macOS apps are in standard locations:

```swift
let standardLocations = [
    "/Applications/",           // User apps
    "/System/Applications/",    // System apps
    "~/Applications/",          // User-specific apps
    "/Library/Application Support/"
]

func matchToInstalledApp(processPath: String, installedApps: [App]) -> App? {
    for app in installedApps {
        // Check if process is inside app bundle
        if let installLocation = app.installLocation {
            // App bundles: /Applications/Docker.app
            // Process: /Applications/Docker.app/Contents/MacOS/Docker
            if processPath.hasPrefix(installLocation) {
                return app
            }
        }
    }
    return nil
}
```

### Bundle Identifier Matching

For apps that spawn helper processes:

```swift
func matchByBundleId(processPath: String, installedApps: [App]) -> App? {
    // Get bundle ID from process's parent bundle
    if let bundleId = getBundleIdForProcess(processPath) {
        return installedApps.first { $0.bundleIdentifier == bundleId }
    }
    return nil
}
```

---

## Testing Your Implementation

### 1. Verify Output Structure

```bash
# After collection, check the JSON output
cat /path/to/cache/applications.json | jq '.usage'
```

Expected:
```json
{
  "isCaptureEnabled": true,
  "captureMethod": "UnifiedLog",
  "activeSessions": [
    {
      "name": "Slack",
      "path": "/Applications/Slack.app/Contents/MacOS/Slack",
      "user": "jsmith",
      "durationSeconds": 28800
    }
  ]
}
```

### 2. Verify No System Processes

The `activeSessions` array should NOT contain:
- launchd
- kernel_task
- mdworker
- cfprefsd
- Any process not in `installedApplications`

### 3. Test API Compatibility

After transmitting to the API:

```bash
curl -s "https://reportmate-functions-api.blackdune-79551938.canadacentral.azurecontainerapps.io/api/device/YOUR_SERIAL" | jq '.applications.usage'
```

---

## API Compatibility Reference

The API expects this exact structure in the `applications` module data:

```typescript
interface ApplicationsData {
  installedApplications: Array<{
    name: string;
    version?: string;
    installLocation?: string;
    publisher?: string;
    installDate?: string;
    bundleIdentifier?: string;  // macOS specific
  }>;
  usage: {
    isCaptureEnabled: boolean;
    captureMethod: string;  // "UnifiedLog", "BSMAudit", "ProcessPolling", "None"
    activeSessions: Array<{
      name: string;           // MUST match an installed app name
      path: string;
      user: string;
      startTime: string;      // ISO 8601
      endTime?: string;       // ISO 8601, null if still running
      durationSeconds: number;
      processId: number;
    }>;
  };
}
```

---

## Differences from Windows

| Aspect | Windows | macOS |
|--------|---------|-------|
| Event Source | Security Log 4688/4689 | Unified Log / BSM Audit |
| App Location | `C:\Program Files\*` | `/Applications/*.app` |
| User Format | `DOMAIN\user` | `username` |
| App Matching | Install path prefix | Bundle path or identifier |
| Capture Method | "SecurityLog" or "KernelProcess" | "UnifiedLog" or "BSMAudit" |

---

## Checklist Before Deployment

- [ ] Usage data is collected from appropriate macOS source
- [ ] Sessions are matched to installed applications ONLY
- [ ] Unmatched processes are discarded (not sent to API)
- [ ] Session names use installed app name (not process name)
- [ ] Duration is calculated in seconds
- [ ] Timestamps are ISO 8601 format
- [ ] JSON structure matches expected API format
- [ ] `isCaptureEnabled` reflects actual capability
- [ ] `captureMethod` indicates the source used
- [ ] Tested end-to-end with API

---

## Questions / Support

If you encounter issues with:
- API compatibility: Check `infrastructure/modules/api/main.py`
- Windows reference: Check `clients/windows/src/Services/ApplicationUsageService.cs`
- Frontend display: Check `apps/www/src/components/reports/FleetApplicationsReport.tsx`

The key principle: **Only installed applications should have utilization data**. This keeps reports clean and actionable.
