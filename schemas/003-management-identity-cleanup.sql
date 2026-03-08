-- Migration: Clean stale identity/joining data from management module
-- Date: 2025-07-01
-- Context: EnrollmentType and DomainTrust have been moved to the identity module.
--          Old management JSONB rows may still contain these fields from prior collections.
--          This script strips them so the management table only holds MDM-related data.
--
-- Safe to run multiple times (idempotent).
-- Affects only the management table's JSONB `data` column.
-- Does NOT delete rows or touch any other table.

BEGIN;

-- 1. Remove enrollmentType from mdmEnrollment nested object
--    Old data: data->'mdmEnrollment'->'enrollmentType'
UPDATE management
SET data = data #- '{mdmEnrollment,enrollmentType}',
    updated_at = NOW()
WHERE data->'mdmEnrollment' ? 'enrollmentType';

-- 2. Remove domainTrust top-level key (moved to identity module)
--    Old data: data->'domainTrust'
UPDATE management
SET data = data - 'domainTrust',
    updated_at = NOW()
WHERE data ? 'domainTrust';

-- 3. Remove enrollment_type at top level (alternate casing from older clients)
UPDATE management
SET data = data - 'enrollment_type',
    updated_at = NOW()
WHERE data ? 'enrollment_type';

-- 4. Remove domain_trust at top level (alternate casing from older clients)
UPDATE management
SET data = data - 'domain_trust',
    updated_at = NOW()
WHERE data ? 'domain_trust';

-- Verify: count remaining rows that still have stale keys
SELECT 'Remaining rows with mdmEnrollment.enrollmentType' AS check_name,
       COUNT(*) AS count
FROM management
WHERE data->'mdmEnrollment' ? 'enrollmentType'
UNION ALL
SELECT 'Remaining rows with domainTrust',
       COUNT(*)
FROM management
WHERE data ? 'domainTrust'
UNION ALL
SELECT 'Remaining rows with enrollment_type',
       COUNT(*)
FROM management
WHERE data ? 'enrollment_type'
UNION ALL
SELECT 'Remaining rows with domain_trust',
       COUNT(*)
FROM management
WHERE data ? 'domain_trust';

COMMIT;
