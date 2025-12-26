#!/usr/bin/env python3
"""
ReportMate Database Maintenance Script
Runs daily via Azure Container Apps Job to prevent database crisis recurrence.
"""

import os
import sys
import psycopg2
from datetime import datetime, timedelta
from typing import Tuple

# Configuration
EVENT_RETENTION_DAYS = int(os.getenv('EVENT_RETENTION_DAYS', '30'))
DB_HOST = os.getenv('DB_HOST', 'reportmate-database.postgres.database.azure.com')
DB_NAME = os.getenv('DB_NAME', 'reportmate')
DB_USER = os.getenv('DB_USER', 'reportmate')
DB_PASS = os.getenv('DB_PASS')

def get_connection():
    """Connect to PostgreSQL database"""
    if not DB_PASS:
        raise ValueError("DB_PASS environment variable not set")
    
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        sslmode='require'
    )

def cleanup_old_events(cursor, retention_days: int) -> int:
    """Delete events older than retention period"""
    cutoff = datetime.now() - timedelta(days=retention_days)
    
    print(f"  Cleaning events older than {cutoff.strftime('%Y-%m-%d')}...")
    cursor.execute("""
        DELETE FROM events 
        WHERE created_at < %s
    """, (cutoff,))
    
    deleted = cursor.rowcount
    print(f"  Deleted {deleted:,} old events")
    return deleted

def remove_duplicate_module_records(cursor) -> int:
    """
    Keep only the newest record per device per module table.
    Each device should have exactly 1 record in each module table.
    """
    print(f"  Removing duplicate module records...")
    
    module_tables = [
        'applications', 'hardware', 'installs', 'network', 
        'security', 'inventory', 'management', 'system', 
        'displays', 'printers'
    ]
    
    total_deleted = 0
    
    for table in module_tables:
        cursor.execute(f"""
            WITH duplicates AS (
                SELECT id, 
                       ROW_NUMBER() OVER (
                           PARTITION BY device_id 
                           ORDER BY updated_at DESC, id DESC
                       ) as rn
                FROM {table}
            )
            DELETE FROM {table}
            WHERE id IN (
                SELECT id FROM duplicates WHERE rn > 1
            )
        """)
        
        deleted = cursor.rowcount
        if deleted > 0:
            print(f"    {table}: removed {deleted} duplicates")
            total_deleted += deleted
    
    print(f"  Total duplicates removed: {total_deleted}")
    return total_deleted

def remove_orphaned_module_records(cursor) -> int:
    """Delete module records for devices that no longer exist"""
    print(f"  Removing orphaned module records...")
    
    module_tables = [
        'applications', 'hardware', 'installs', 'network', 
        'security', 'inventory', 'management', 'system',
        'displays', 'printers'
    ]
    
    total_deleted = 0
    
    for table in module_tables:
        cursor.execute(f"""
            DELETE FROM {table}
            WHERE device_id NOT IN (
                SELECT serial_number FROM devices
            )
        """)
        
        deleted = cursor.rowcount
        if deleted > 0:
            print(f"    {table}: removed {deleted} orphans")
            total_deleted += deleted
    
    print(f"  Total orphans removed: {total_deleted}")
    return total_deleted

def cleanup_orphaned_policies(cursor) -> int:
    """Remove policies from catalog that are no longer referenced by any device"""
    print(f"  Cleaning orphaned policies from catalog...")
    
    # Check if policy_catalog table exists (policy deduplication may not be deployed yet)
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'policy_catalog'
        )
    """)
    
    if not cursor.fetchone()[0]:
        print(f"    Policy deduplication not yet enabled")
        return 0
    
    # Delete policies not referenced by any device
    cursor.execute("""
        DELETE FROM policy_catalog
        WHERE policy_hash NOT IN (
            SELECT DISTINCT unnest(
                COALESCE(intune_policy_hashes, '{}') || 
                COALESCE(security_policy_hashes, '{}') || 
                COALESCE(mdm_policy_hashes, '{}')
            ) FROM profiles
        )
    """)
    
    deleted = cursor.rowcount
    
    # Update device counts for remaining policies
    cursor.execute("""
        UPDATE policy_catalog pc
        SET device_count = (
            SELECT COUNT(DISTINCT p.device_id)
            FROM profiles p
            WHERE pc.policy_hash = ANY(
                COALESCE(p.intune_policy_hashes, '{}') || 
                COALESCE(p.security_policy_hashes, '{}') || 
                COALESCE(p.mdm_policy_hashes, '{}')
            )
        )
    """)
    
    print(f"  Removed {deleted} orphaned policies, updated device counts")
    return deleted

def optimize_database(cursor) -> None:
    """Run VACUUM ANALYZE to reclaim space and update statistics"""
    print(f"  Running VACUUM ANALYZE...")
    
    # Need to commit first and run VACUUM outside transaction
    cursor.connection.commit()
    
    # Set autocommit for VACUUM
    old_isolation = cursor.connection.isolation_level
    cursor.connection.set_isolation_level(0)
    
    try:
        cursor.execute("VACUUM ANALYZE")
        print(f"  VACUUM completed successfully")
    finally:
        cursor.connection.set_isolation_level(old_isolation)

def get_database_stats(cursor) -> dict:
    """Get database size statistics"""
    cursor.execute("""
        SELECT 
            pg_size_pretty(pg_database_size(current_database())) as total_size,
            (SELECT COUNT(*) FROM events) as event_count,
            (SELECT COUNT(*) FROM devices) as device_count,
            (SELECT COUNT(*) FROM policy_catalog) as policy_count
    """)
    
    row = cursor.fetchone()
    return {
        'total_size': row[0],
        'event_count': row[1],
        'device_count': row[2],
        'policy_count': row[3]
    }

def main():
    """Main maintenance routine"""
    print(f"\n{'='*60}")
    print(f"ReportMate Database Maintenance")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"{'='*60}\n")
    
    try:
        # Connect to database
        print(f"Connecting to database...")
        conn = get_connection()
        cursor = conn.cursor()
        print(f"  Connected successfully\n")
        
        # Get initial stats
        print(f"Database stats (before):")
        stats_before = get_database_stats(cursor)
        for key, value in stats_before.items():
            print(f"  {key}: {value}")
        print()
        
        # Run cleanup tasks
        print(f"Running cleanup tasks:\n")
        
        events_deleted = cleanup_old_events(cursor, EVENT_RETENTION_DAYS)
        print()
        
        duplicates_deleted = remove_duplicate_module_records(cursor)
        print()
        
        orphans_deleted = remove_orphaned_module_records(cursor)
        print()
        
        policies_deleted = cleanup_orphaned_policies(cursor)
        print()
        
        # Commit changes
        conn.commit()
        print(f"Changes committed\n")
        
        # Optimize database (if significant deletions)
        if events_deleted > 1000 or duplicates_deleted > 10 or orphans_deleted > 10:
            optimize_database(cursor)
            print()
        else:
            print(f"Skipping VACUUM (minimal deletions)\n")
        
        # Get final stats
        print(f"Database stats (after):")
        stats_after = get_database_stats(cursor)
        for key, value in stats_after.items():
            print(f"  {key}: {value}")
        print()
        
        # Summary
        print(f"{'='*60}")
        print(f"Maintenance Summary:")
        print(f"  Events deleted: {events_deleted:,}")
        print(f"  Duplicates removed: {duplicates_deleted:,}")
        print(f"  Orphans removed: {orphans_deleted:,}")
        print(f"  Policies cleaned: {policies_deleted:,}")
        print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"{'='*60}\n")
        
        cursor.close()
        conn.close()
        
        return 0
        
    except Exception as e:
        print(f"\nERROR: {str(e)}", file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
