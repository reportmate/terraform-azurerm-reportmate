-- Bulk security endpoint: /api/devices/security
-- Returns devices with structured security summary fields
-- Extracts fields needed by the frontend fleet security page
-- Parameters: include_archived (boolean)

SELECT DISTINCT ON (d.serial_number)
    d.serial_number,
    d.device_id,
    d.last_seen,
    d.platform,
    sec.collected_at,
    -- Inventory fields
    COALESCE(inv.data->>'device_name', inv.data->>'deviceName') as device_name,
    COALESCE(inv.data->>'computer_name', inv.data->>'computerName') as computer_name,
    inv.data->>'usage' as usage,
    inv.data->>'catalog' as catalog,
    inv.data->>'location' as location,
    COALESCE(inv.data->>'asset_tag', inv.data->>'assetTag') as asset_tag,
    inv.data->>'department' as department,
    inv.data->>'fleet' as fleet,

    -- Firewall
    COALESCE(
        (sec.data->'firewall'->>'isEnabled')::boolean,
        (sec.data->'firewall'->>'enabled')::boolean,
        CASE WHEN sec.data->'firewall'->>'globalState' IN ('on', '1') THEN true ELSE false END
    ) as firewall_enabled,

    -- Encryption (Windows: bitLocker, Mac: fileVault)
    -- Guard against the osquery Win11 26100 bug where bitlocker_info reports
    -- protection_status=1 on unencrypted drives. Trust isEnabled only when at
    -- least one encrypted volume has a real encryption method ("AES-*", not "None").
    -- jsonb_typeof guard protects against malformed payloads where encryptedVolumes
    -- is null/object/scalar — calling jsonb_array_elements on a non-array would
    -- otherwise break the entire /api/devices/security query.
    COALESCE(
        CASE
            WHEN (sec.data->'encryption'->'bitLocker'->>'isEnabled')::boolean = true
             AND jsonb_typeof(sec.data->'encryption'->'encryptedVolumes') = 'array'
             AND EXISTS (
                SELECT 1 FROM jsonb_array_elements(sec.data->'encryption'->'encryptedVolumes') vol
                WHERE COALESCE(vol->>'encryptionMethod', 'None') NOT IN ('None', '')
            ) THEN true
            WHEN (sec.data->'encryption'->'bitLocker'->>'isEnabled')::boolean = true THEN false
            ELSE NULL
        END,
        (sec.data->'fileVault'->>'enabled')::boolean,
        false
    ) as encryption_enabled,

    -- Antivirus
    COALESCE(sec.data->'antivirus'->>'name', '') as antivirus_name,
    COALESCE((sec.data->'antivirus'->>'isEnabled')::boolean, false) as antivirus_enabled,
    COALESCE((sec.data->'antivirus'->>'isUpToDate')::boolean, false) as antivirus_up_to_date,
    sec.data->'antivirus'->>'version' as antivirus_version,
    sec.data->'antivirus'->>'lastScan' as antivirus_last_scan,

    -- Detection: raw event count (includes ASR blocks, not just active threats)
    COALESCE(jsonb_array_length(sec.data->'detections'), 0) as detection_count,
    -- Active threats only (excludes ASR rule blocks which are protection working)
    -- ASR blocks are category='ASR Rule' or eventId=1121
    COALESCE((
        SELECT count(*)::int FROM jsonb_array_elements(sec.data->'detections') det
        WHERE COALESCE(det->>'category', '') NOT IN ('ASR Rule')
          AND COALESCE((det->>'eventId')::int, 0) NOT IN (1121)
    ), 0) as active_threat_count,
    -- Detection summary fields populated by the client
    COALESCE((sec.data->'detectionSummary'->>'hasActiveThreats')::boolean, false) as has_active_threats,
    COALESCE((sec.data->'detectionSummary'->>'totalBlocked30d')::int, 0) as detections_blocked_30d,
    COALESCE((sec.data->'detectionSummary'->>'totalCleaned30d')::int, 0) as detections_cleaned_30d,
    COALESCE((sec.data->'detectionSummary'->>'totalDetections30d')::int, 0) as detections_total_30d,
    sec.data->'detectionSummary'->>'lastThreatDetectedAt' as last_threat_detected_at,

    -- Tampering: TPM (Windows)
    COALESCE((sec.data->'tpm'->>'isPresent')::boolean, false) as tpm_present,
    COALESCE((sec.data->'tpm'->>'isEnabled')::boolean, false) as tpm_enabled,
    -- Tampering: Secure Boot
    COALESCE((sec.data->'secureBoot'->>'isEnabled')::boolean, false) as secure_boot_enabled,
    -- Secure Boot UEFI certificate counts (DB = trusted signatures, KEK = key exchange keys)
    COALESCE(jsonb_array_length(sec.data->'secureBoot'->'dbCertificates'), 0) as secure_boot_db_cert_count,
    COALESCE(jsonb_array_length(sec.data->'secureBoot'->'kekCertificates'), 0) as secure_boot_kek_cert_count,
    -- Tampering: SIP (macOS)
    COALESCE(
        (sec.data->'systemIntegrityProtection'->>'enabled')::boolean,
        (sec.data->>'sipEnabled')::boolean
    ) as sip_enabled,
    -- Tampering: Gatekeeper (macOS)
    COALESCE(
        (sec.data->'gatekeeper'->>'enabled')::boolean,
        false
    ) as gatekeeper_enabled,

    -- Firmware Password
    -- Windows clients populate firmwarePassword.statusDisplay ("Set"/"Not Set"/"Not Implemented"/"Unknown")
    -- macOS clients populate firmwarePassword.enabled (boolean)
    COALESCE(
        sec.data->'firmwarePassword'->>'statusDisplay',
        CASE
            WHEN (sec.data->'firmwarePassword'->>'enabled')::boolean = true THEN 'Set'
            WHEN (sec.data->'firmwarePassword'->>'enabled')::boolean = false THEN 'Not Set'
            ELSE NULL
        END
    ) as firmware_password_status,

    -- Device Guard / Protection (Windows)
    COALESCE((sec.data->'deviceGuard'->>'memoryIntegrityEnabled')::boolean, false) as memory_integrity_enabled,
    COALESCE((sec.data->'deviceGuard'->>'coreIsolationEnabled')::boolean, false) as core_isolation_enabled,
    sec.data->'deviceGuard'->>'smartAppControlState' as smart_app_control_state,

    -- Remote Access: SSH
    sec.data->'secureShell'->>'statusDisplay' as ssh_status_display,
    COALESCE((sec.data->'secureShell'->>'isConfigured')::boolean, false) as ssh_is_configured,
    COALESCE((sec.data->'secureShell'->>'isServiceRunning')::boolean, false) as ssh_is_service_running,
    -- Remote Access: RDP (Windows)
    COALESCE((sec.data->'rdp'->>'isEnabled')::boolean, false) as rdp_enabled,

    -- Certificates: prefer client-computed summary when present, fall back to JSONB scan
    COALESCE(
        (sec.data->'certificateSummary'->>'totalCount')::int,
        jsonb_array_length(sec.data->'certificates'),
        0
    ) as certificate_count,
    COALESCE(
        (sec.data->'certificateSummary'->>'expiredCount')::int,
        (SELECT count(*)::int FROM jsonb_array_elements(sec.data->'certificates') cert
         WHERE (cert->>'isExpired')::boolean = true),
        0
    ) as expired_cert_count,
    COALESCE(
        (sec.data->'certificateSummary'->>'expiringSoonCount')::int,
        (SELECT count(*)::int FROM jsonb_array_elements(sec.data->'certificates') cert
         WHERE (cert->>'isExpiringSoon')::boolean = true),
        0
    ) as expiring_soon_cert_count,
    -- Split expired into user-managed vs OS-bundled roots so the UI can de-noise OS rotations
    COALESCE((sec.data->'certificateSummary'->>'userExpiredCount')::int, 0) as user_expired_cert_count,
    COALESCE((sec.data->'certificateSummary'->>'osRootExpiredCount')::int, 0) as os_root_expired_cert_count,

    -- Vulnerabilities: read from the securityCves array (top-level cveCount was never populated by the client)
    COALESCE((
        SELECT count(*)::int FROM jsonb_array_elements(sec.data->'securityCves') cve
        WHERE COALESCE(cve->>'status', '') = 'Unpatched'
    ), 0) as cve_count,
    COALESCE((
        SELECT count(*)::int FROM jsonb_array_elements(sec.data->'securityCves') cve
        WHERE COALESCE(cve->>'status', '') = 'Unpatched'
          AND COALESCE(cve->>'severity', '') = 'Critical'
    ), 0) as critical_cve_count,
    -- Actively exploited unpatched CVEs (KEV-style)
    COALESCE((
        SELECT count(*)::int FROM jsonb_array_elements(sec.data->'securityCves') cve
        WHERE COALESCE(cve->>'status', '') = 'Unpatched'
          AND COALESCE((cve->>'activelyExploited')::boolean, false) = true
    ), 0) as actively_exploited_cve_count,

    -- Phase 2: protection posture
    COALESCE((sec.data->'lsaProtection'->>'enabled')::boolean, false) as lsa_protection_enabled,
    sec.data->'lsaProtection'->>'mode' as lsa_protection_mode,
    (sec.data->'tamperProtection'->>'isTamperProtected')::boolean as tamper_protected,
    sec.data->'uac'->>'level' as uac_level,
    COALESCE((sec.data->'pendingReboot'->>'required')::boolean, false) as pending_reboot,
    COALESCE((
        SELECT count(*)::int FROM jsonb_array_elements(sec.data->'asrRules') rule
        WHERE COALESCE(rule->>'state', '') = 'Block'
    ), 0) as asr_block_rule_count,
    COALESCE((
        SELECT count(*)::int FROM jsonb_array_elements(sec.data->'asrRules') rule
        WHERE COALESCE(rule->>'state', '') = 'Audit'
    ), 0) as asr_audit_rule_count,
    sec.data->'defenderVersions'->>'amEngineVersion' as defender_engine_version,
    sec.data->'defenderVersions'->>'amProductVersion' as defender_product_version,
    COALESCE((sec.data->'defenderExclusions'->>'totalCount')::int, 0) as defender_exclusions_count,
    (sec.data->'joinState'->>'azureAdJoined')::boolean as entra_joined,
    (sec.data->'joinState'->>'domainJoined')::boolean as domain_joined,
    sec.data->'joinState'->>'tenantName' as entra_tenant_name,

    -- Phase 3: compliance / inventory
    COALESCE(jsonb_array_length(sec.data->'localAdmins'), 0) as local_admin_count,
    COALESCE(
        (sec.data->'laps'->>'windowsLapsConfigured')::boolean
        OR (sec.data->'laps'->>'legacyLapsInstalled')::boolean,
        false
    ) as laps_configured,
    sec.data->'laps'->>'backupDirectory' as laps_backup_directory,
    COALESCE((sec.data->'appLocker'->>'policyConfigured')::boolean, false) as applocker_configured,
    COALESCE((sec.data->'appLocker'->>'wdacEnabled')::boolean, false) as wdac_enabled,
    sec.data->'smartScreen'->>'windowsState' as smartscreen_state,
    (sec.data->'smartScreen'->>'edgeEnabled')::boolean as edge_smartscreen_enabled,
    COALESCE(jsonb_array_length(sec.data->'auditPolicy'->'categories'), 0) as audit_policy_count,
    COALESCE(jsonb_array_length(sec.data->'edrProducts'), 0) as edr_product_count,
    COALESCE(
        (sec.data->'windowsHello'->>'faceSensorPresent')::boolean
        OR (sec.data->'windowsHello'->>'fingerprintSensorPresent')::boolean,
        false
    ) as hello_biometric_present,
    COALESCE((sec.data->'tpmOwnership'->>'isOwned')::boolean, false) as tpm_owned,
    COALESCE((sec.data->'tpmOwnership'->>'isReady')::boolean, false) as tpm_ready,
    (sec.data->'passwordPolicy'->>'minPasswordLength')::int as min_password_length,
    (sec.data->'passwordPolicy'->>'lockoutThreshold')::int as lockout_threshold,
    COALESCE((sec.data->'autoLogin'->>'autoAdminLogon')::boolean, false) as auto_admin_logon,
    COALESCE((sec.data->'autoLogin'->>'hasDefaultPassword')::boolean, false) as default_password_present,

    -- Misc
    COALESCE(sec.data->'autoLogin'->>'defaultUserName', sec.data->>'autoLoginUser') as auto_login_user

FROM devices d
LEFT JOIN security sec ON d.serial_number = sec.device_id
LEFT JOIN inventory inv ON d.serial_number = inv.device_id
WHERE d.serial_number IS NOT NULL
    AND d.serial_number NOT LIKE 'TEST-%%'
    AND d.serial_number != 'localhost'
    AND sec.data IS NOT NULL
    AND (%(include_archived)s = TRUE OR d.archived = FALSE)
ORDER BY d.serial_number, sec.updated_at DESC;
