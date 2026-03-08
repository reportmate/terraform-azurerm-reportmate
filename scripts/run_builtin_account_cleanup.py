#!/usr/bin/env python3
"""
Run the cleanup-builtin-windows-accounts.sql against the production database.
Fetches DB credentials from environment variables or Key Vault.

Usage:
    DB_HOST=... DB_USER=... DB_NAME=... DB_PASS=... python run_builtin_account_cleanup.py
"""
import os
import sys

import pg8000.native

DB_HOST = os.environ.get("DB_HOST", "reportmate-database.postgres.database.azure.com")
DB_USER = os.environ.get("DB_USER", "reportmate")
DB_NAME = os.environ.get("DB_NAME", "reportmate")
DB_PASS = os.environ.get("DB_PASS", "")

if not DB_PASS:
    print("ERROR: DB_PASS environment variable is required")
    sys.exit(1)

conn = pg8000.native.Connection(
    host=DB_HOST,
    database=DB_NAME,
    user=DB_USER,
    password=DB_PASS,
    ssl_context=True
)

BUILTIN_SID_PATTERN = r"-(500|501|503|504)$"
BUILTIN_USERNAMES = "('administrator', 'guest', 'defaultaccount', 'wdagutilityaccount')"

print("=== Built-in Windows Account Cleanup ===")
print(f"Database: {DB_HOST}/{DB_NAME}")
print()

# Step 1: Preview
rows = conn.run(f"""
    SELECT
        COUNT(DISTINCT i.device_id) AS devices_with_builtin_accounts,
        COUNT(*) AS total_builtin_account_entries
    FROM identity i,
         jsonb_array_elements(i.data->'users') AS u
    WHERE (u->>'sid') ~ '{BUILTIN_SID_PATTERN}'
       OR lower(u->>'username') IN {BUILTIN_USERNAMES}
""")
devices_before = rows[0][0]
entries_before = rows[0][1]
print(f"Before: {devices_before} devices affected, {entries_before} built-in account entries")

if entries_before == 0:
    print("Nothing to clean up — database is already clean.")
    conn.close()
    sys.exit(0)

# Step 2: Update
conn.run(f"""
    UPDATE identity
    SET
        data = jsonb_set(
            data,
            '{{users}}',
            COALESCE(
                (
                    SELECT jsonb_agg(u)
                    FROM jsonb_array_elements(data->'users') AS u
                    WHERE NOT (
                        (u->>'sid') ~ '{BUILTIN_SID_PATTERN}'
                        OR lower(u->>'username') IN {BUILTIN_USERNAMES}
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
            WHERE (u->>'sid') ~ '{BUILTIN_SID_PATTERN}'
               OR lower(u->>'username') IN {BUILTIN_USERNAMES}
        )
""")
print("Cleanup UPDATE executed successfully")

# Step 3: Verify
rows = conn.run(f"""
    SELECT
        COUNT(DISTINCT i.device_id) AS remaining_devices,
        COUNT(*) AS remaining_entries
    FROM identity i,
         jsonb_array_elements(i.data->'users') AS u
    WHERE (u->>'sid') ~ '{BUILTIN_SID_PATTERN}'
       OR lower(u->>'username') IN {BUILTIN_USERNAMES}
""")
devices_after = rows[0][0]
entries_after = rows[0][1]
print(f"After:  {devices_after} devices affected, {entries_after} built-in account entries")

if entries_after == 0:
    print()
    print(f"Done. Removed {entries_before} built-in account entries from {devices_before} devices.")
else:
    print()
    print(f"WARNING: {entries_after} entries still remain — review manually.")

conn.close()
