-- cleanup-builtin-windows-accounts.sql
--
-- Removes well-known Windows built-in accounts from the identity.data->>'users' JSONB array
-- for all devices. Safe to re-run: idempotent (rows with no matching accounts are unchanged).
--
-- Built-in accounts filtered by well-known SID RIDs (locale-independent):
--   RID 500 - Administrator
--   RID 501 - Guest
--   RID 503 - DefaultAccount
--   RID 504 - WDAGUtilityAccount (Windows Defender Application Guard)
--
-- Usage:
--   psql -h <host> -U <user> -d <db> -f cleanup-builtin-windows-accounts.sql
--   or run via run-migrations.ps1 / the API /api/admin/migrate endpoint

-- -----------------------------------------------------------------------
-- Step 1: Preview — count affected rows before making any changes
-- -----------------------------------------------------------------------
SELECT
    COUNT(DISTINCT i.device_id) AS devices_with_builtin_accounts,
    COUNT(*) AS total_builtin_account_entries
FROM identity i,
     jsonb_array_elements(i.data->'users') AS u
WHERE (u->>'sid') ~ '-(500|501|503|504)$'
   OR lower(u->>'username') IN ('administrator', 'guest', 'defaultaccount', 'wdagutilityaccount');

-- -----------------------------------------------------------------------
-- Step 2: Remove the built-in accounts from the users array in-place
-- -----------------------------------------------------------------------
UPDATE identity
SET
    data = jsonb_set(
        data,
        '{users}',
        COALESCE(
            (
                SELECT jsonb_agg(u)
                FROM jsonb_array_elements(data->'users') AS u
                WHERE NOT (
                    (u->>'sid') ~ '-(500|501|503|504)$'
                    OR lower(u->>'username') IN ('administrator', 'guest', 'defaultaccount', 'wdagutilityaccount')
                )
            ),
            '[]'::jsonb
        )
    ),
    updated_at = NOW()
WHERE
    data->'users' IS NOT NULL
    AND EXISTS (
        SELECT 1
        FROM jsonb_array_elements(data->'users') AS u
        WHERE (u->>'sid') ~ '-(500|501|503|504)$'
           OR lower(u->>'username') IN ('administrator', 'guest', 'defaultaccount', 'wdagutilityaccount')
    );

-- -----------------------------------------------------------------------
-- Step 3: Verify — should return 0 rows after cleanup
-- -----------------------------------------------------------------------
SELECT
    COUNT(DISTINCT i.device_id) AS remaining_devices_with_builtin_accounts,
    COUNT(*) AS remaining_builtin_account_entries
FROM identity i,
     jsonb_array_elements(i.data->'users') AS u
WHERE (u->>'sid') ~ '-(500|501|503|504)$'
   OR lower(u->>'username') IN ('administrator', 'guest', 'defaultaccount', 'wdagutilityaccount');
