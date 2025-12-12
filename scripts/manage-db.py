#!/usr/bin/env python3
"""
ReportMate Database Management Utility
Script for database management operations
Reads credentials from terraform.tfvars for security
"""

import os
import sys
import argparse
import re
import pg8000
from pathlib import Path

# Fix Windows PowerShell Unicode encoding issues
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# ANSI color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[96m'
RESET = '\033[0m'
BOLD = '\033[1m'

def print_header(text):
    """Print formatted header"""
    print(f"\n{CYAN}{'=' * 70}{RESET}")
    print(f"{BOLD}{text}{RESET}")
    print(f"{CYAN}{'=' * 70}{RESET}\n")

def print_success(text):
    """Print success message"""
    print(f"{GREEN}[OK] {text}{RESET}")

def print_error(text):
    """Print error message"""
    print(f"{RED}[ERR] {text}{RESET}")

def print_warning(text):
    """Print warning message"""
    print(f"{YELLOW}[WARN] {text}{RESET}")

def print_info(text):
    """Print info message"""
    print(f"{BLUE}[INFO] {text}{RESET}")

def get_db_password_from_tfvars():
    """
    Securely read database password from terraform.tfvars
    This is the preferred method as it keeps credentials in infrastructure config
    """
    # Try multiple paths to find terraform.tfvars
    possible_paths = [
        Path(__file__).parent.parent / 'terraform.tfvars',  # infrastructure/terraform.tfvars
        Path(__file__).parent.parent.parent / 'infrastructure' / 'terraform.tfvars',  # from repo root
        Path.cwd() / 'infrastructure' / 'terraform.tfvars',  # from current working directory
        Path.cwd() / 'terraform.tfvars',  # if already in infrastructure/
    ]
    
    for tfvars_path in possible_paths:
        if tfvars_path.exists():
            try:
                print_info(f"Reading credentials from: {tfvars_path}")
                with open(tfvars_path, 'r') as f:
                    content = f.read()
                    
                # Parse db_password using regex (handles quoted and unquoted values)
                match = re.search(r'db_password\s*=\s*"([^"]+)"', content)
                if match:
                    print_success("Loaded database password from terraform.tfvars")
                    return match.group(1)
                    
            except Exception as e:
                print_warning(f"Could not read {tfvars_path}: {e}")
                continue
    
    return None

def get_db_credentials(args):
    """
    Get database credentials with secure fallback chain:
    1. terraform.tfvars (most secure, preferred)
    2. Environment variable DB_PASSWORD
    3. Command-line flag --password (least secure, for emergency use only)
    """
    # Priority 1: terraform.tfvars (secure, infrastructure-integrated)
    password = get_db_password_from_tfvars()
    if password:
        return {
            'host': os.getenv('DB_SERVER', 'reportmate-database.postgres.database.azure.com'),
            'database': os.getenv('DB_NAME', 'reportmate'),
            'user': os.getenv('DB_USER', 'reportmate'),
            'password': password,
            'source': 'terraform.tfvars'
        }
    
    # Priority 2: Environment variable (secure, temporary)
    password = os.getenv('DB_PASSWORD')
    if password:
        print_info("Using DB_PASSWORD from environment variable")
        return {
            'host': os.getenv('DB_SERVER', 'reportmate-database.postgres.database.azure.com'),
            'database': os.getenv('DB_NAME', 'reportmate'),
            'user': os.getenv('DB_USER', 'reportmate'),
            'password': password,
            'source': 'environment'
        }
    
    # Priority 3: Command-line flag (least secure, emergency only)
    if args.password:
        print_warning("Using password from command-line flag (visible in process list!)")
        return {
            'host': os.getenv('DB_SERVER', 'reportmate-database.postgres.database.azure.com'),
            'database': os.getenv('DB_NAME', 'reportmate'),
            'user': os.getenv('DB_USER', 'reportmate'),
            'password': args.password,
            'source': 'command-line'
        }
    
    # No password found
    print_error("No database password found!")
    print_info("\nTry one of these methods:")
    print_info("  1. [PREFERRED] Ensure terraform.tfvars exists in infrastructure/")
    print_info("  2. Set environment: $env:DB_PASSWORD = 'your_password'")
    print_info("  3. Use flag: --password 'your_password' (not recommended)")
    sys.exit(1)

def connect_db(creds):
    """Connect to PostgreSQL database"""
    print_info(f"Connecting to {creds['host']}/{creds['database']} as {creds['user']}...")
    print_info(f"Credentials source: {creds['source']}")
    
    try:
        conn = pg8000.connect(
            host=creds['host'],
            database=creds['database'],
            user=creds['user'],
            password=creds['password'],
            ssl_context=True
        )
        cursor = conn.cursor()
        print_success("Connected to database")
        return conn, cursor
    except Exception as e:
        print_error(f"Connection failed: {e}")
        sys.exit(1)

def cleanup_hostnames(cursor, conn, dry_run=False, auto_confirm=False):
    """
    Remove devices with hostname patterns instead of real serial numbers
    
    This matches the validation logic from:
    1. API endpoint (/api/device) - Rejects hostname patterns at ingestion
    2. Client code (ApiService.cs) - Prevents hostname fallback at transmission
    
    Hostname patterns detected (matching API validation):
    - ^[A-Z]+-[A-Z]+$ : Name patterns (TOLUWANI-AGBI, AWI-JUMP, NICOLE-ALMEIDA)
    - ^[A-Z]+\\-[A-Z0-9]+\\-[A-Z0-9]+$ : DESKTOP-ABC123 patterns
    - ^WIN-[A-Z0-9]+$ : Windows default hostnames (WIN-GM0MB0JR)
    - ^[A-Z]+-[A-Z]+-[A-Z]+-[0-9]+$ : Lab/Room patterns (ANIM-STD-LAB-11)
    - ^[A-Z]{4,}-[0-9]{4}$ : Username-Device patterns (JMCVEITY-0322)
    - ^[A-Z]{2,}\\d{2,}$ : Numbered hostnames (DESKTOP01, TESTDEV001)
    - Only letters/hyphens : Serial numbers should contain numbers
    
    Real hardware serials contain numbers and don't follow hostname conventions.
    Client should NEVER fall back to Environment.MachineName - serial or FAIL.
    """
    print_header("Cleanup: Hostname-Based Devices")
    
    # Query to find hostname patterns
    # MATCHES API VALIDATION: infrastructure/modules/api/main.py @device_events endpoint
    # MATCHES CLIENT GATE: clients/windows/src/Services/ApiService.cs line 112-124
    hostname_patterns = """
    WHERE 
        serial_number ~ '^[A-Z]+-[A-Z]+$'
        OR serial_number ~ '^(DESKTOP|LAPTOP|WORKSTATION|PC)-[A-Z0-9]+$'
        OR serial_number ~ '^WIN-[A-Z0-9]+$'
        OR serial_number ~ '^[A-Z]+-[A-Z]+-[A-Z]+-[0-9]+$'
        OR serial_number ~ '^[A-Z]{4,}-[0-9]{4}$'
        OR serial_number ~ '^[A-Z]{2,}[0-9]{2,}$'
        OR (serial_number ~ '^[A-Z\\-]+$' AND serial_number !~ '[0-9]')
    """
    
    # Count devices
    count_query = f"SELECT COUNT(*) FROM devices {hostname_patterns}"
    cursor.execute(count_query)
    count = cursor.fetchone()[0]
    
    if count == 0:
        print_success("No hostname-based devices found. Database is clean!")
        return
    
    print_info(f"Found {count} hostname-based devices")
    
    # List devices
    list_query = f"""
    SELECT id, serial_number, name, last_seen
    FROM devices {hostname_patterns}
    ORDER BY last_seen DESC
    LIMIT 50
    """
    
    cursor.execute(list_query)
    devices = cursor.fetchall()
    
    print(f"\n{'Serial Number':<25} {'Name':<30} {'Last Seen'}")
    print("-" * 80)
    for device in devices:
        id_val, serial, name, last_seen = device
        print(f"{serial:<25} {name:<30} {str(last_seen)[:19]}")
    
    if len(devices) == 50 and count > 50:
        print(f"\n... and {count - 50} more")
    
    if dry_run:
        print_info("\n[DRY RUN] Would delete these devices")
        return
    
    # Confirm deletion
    print_warning(f"\nAbout to DELETE {count} devices permanently!")
    print_warning("This will CASCADE delete all related module data and events")
    
    if not auto_confirm:
        response = input(f"\n{YELLOW}Type 'DELETE' to confirm: {RESET}")
        if response.strip() != 'DELETE':
            print_info("Deletion cancelled")
            return
    
    # Execute deletion
    print_info("\nExecuting deletion...")
    delete_query = f"DELETE FROM devices {hostname_patterns}"
    cursor.execute(delete_query)
    deleted_count = cursor.rowcount
    conn.commit()
    
    print_success(f"Deleted {deleted_count} hostname-based devices")
    
    # Verify
    cursor.execute(count_query)
    remaining = cursor.fetchone()[0]
    
    if remaining == 0:
        print_success(f"Verification passed: 0 hostname devices remain")
    else:
        print_error(f"Verification failed: {remaining} hostname devices still remain!")

def cleanup_win_prefix(cursor, conn, dry_run=False, auto_confirm=False):
    """Remove devices with WIN- prefix (Windows default hostname pattern)"""
    print_header("Cleanup: WIN- Prefix Devices")
    
    # Count devices
    count_query = "SELECT COUNT(*) FROM devices WHERE serial_number LIKE 'WIN-%'"
    cursor.execute(count_query)
    count = cursor.fetchone()[0]
    
    if count == 0:
        print_success("No WIN- prefix devices found. Database is clean!")
        return
    
    print_info(f"Found {count} WIN- prefix devices")
    
    # List devices
    list_query = """
    SELECT id, serial_number, name, last_seen
    FROM devices
    WHERE serial_number LIKE 'WIN-%'
    ORDER BY last_seen DESC
    """
    
    cursor.execute(list_query)
    devices = cursor.fetchall()
    
    print(f"\n{'Serial Number':<25} {'Name':<30} {'Last Seen'}")
    print("-" * 80)
    for device in devices:
        id_val, serial, name, last_seen = device
        print(f"{serial:<25} {name:<30} {str(last_seen)[:19]}")
    
    if dry_run:
        print_info("\n[DRY RUN] Would delete these devices")
        return
    
    # Confirm deletion
    print_warning(f"\nAbout to DELETE {count} devices permanently!")
    
    if not auto_confirm:
        response = input(f"\n{YELLOW}Type 'DELETE' to confirm: {RESET}")
        if response.strip() != 'DELETE':
            print_info("Deletion cancelled")
            return
    
    # Execute deletion
    print_info("\nExecuting deletion...")
    delete_query = "DELETE FROM devices WHERE serial_number LIKE 'WIN-%'"
    cursor.execute(delete_query)
    deleted_count = cursor.rowcount
    conn.commit()
    
    print_success(f"Deleted {deleted_count} WIN- prefix devices")

def cleanup_duplicates(cursor, conn, dry_run=False, auto_confirm=False):
    """Remove duplicate device registrations (keep most recent)"""
    print_header("Cleanup: Duplicate Devices")
    
    # Find duplicates
    dupe_query = """
    SELECT serial_number, COUNT(*) as count
    FROM devices
    GROUP BY serial_number
    HAVING COUNT(*) > 1
    ORDER BY count DESC
    """
    
    cursor.execute(dupe_query)
    duplicates = cursor.fetchall()
    
    if not duplicates:
        print_success("No duplicate devices found. Database is clean!")
        return
    
    total_dupes = sum(count - 1 for _, count in duplicates)
    print_info(f"Found {len(duplicates)} serial numbers with duplicates ({total_dupes} extra records)")
    
    print(f"\n{'Serial Number':<25} {'Duplicate Count'}")
    print("-" * 50)
    for serial, count in duplicates[:20]:
        print(f"{serial:<25} {count}")
    
    if len(duplicates) > 20:
        print(f"\n... and {len(duplicates) - 20} more")
    
    if dry_run:
        print_info(f"\n[DRY RUN] Would delete {total_dupes} duplicate records")
        return
    
    # Confirm deletion
    print_warning(f"\nAbout to DELETE {total_dupes} duplicate records (keeping most recent)")
    
    if not auto_confirm:
        response = input(f"\n{YELLOW}Type 'DELETE' to confirm: {RESET}")
        if response.strip() != 'DELETE':
            print_info("Deletion cancelled")
            return
    
    # Delete duplicates (keep newest)
    print_info("\nDeleting duplicate records...")
    delete_query = """
    DELETE FROM devices
    WHERE id IN (
        SELECT id FROM (
            SELECT id, serial_number,
                   ROW_NUMBER() OVER (PARTITION BY serial_number ORDER BY last_seen DESC) as rn
            FROM devices
        ) t
        WHERE t.rn > 1
    )
    """
    
    cursor.execute(delete_query)
    deleted_count = cursor.rowcount
    conn.commit()
    
    print_success(f"Deleted {deleted_count} duplicate records")

def validate_serial_patterns(cursor):
    """
    Validate serial numbers against hostname patterns
    Shows breakdown of different hostname pattern types
    Matches API validation logic from infrastructure/modules/api/main.py
    """
    print_header("Serial Number Pattern Validation")
    
    patterns = [
        ("Name patterns (FIRSTNAME-LASTNAME)", r"^[A-Z]+-[A-Z]+$", None),
        ("Windows hostnames (WIN-*)", r"^WIN-[A-Z0-9]+$", None),
        ("Desktop/Laptop patterns", r"^(DESKTOP|LAPTOP|WORKSTATION|PC)-[A-Z0-9]+$", None),
        ("Lab/Room patterns (ANIM-STD-LAB-11)", r"^[A-Z]+-[A-Z]+-[A-Z]+-[0-9]+$", None),
        ("Username-Device patterns (JMCVEITY-0322)", r"^[A-Z]{4,}-[0-9]{4}$", None),
        ("Numbered hostnames (DESKTOP01)", r"^[A-Z]{2,}[0-9]{2,}$", None),
        ("Only letters (no numbers)", r"^[A-Z\-]+$", r"serial_number !~ '[0-9]'"),
    ]
    
    print_info("Checking serial numbers against hostname patterns...")
    print_info("(Real hardware serials should have numbers and not match these patterns)\n")
    
    total_issues = 0
    for description, pattern, additional_check in patterns:
        if additional_check:
            # Special case for "only letters" pattern with additional condition
            query = f"SELECT COUNT(*) FROM devices WHERE serial_number ~ '{pattern}' AND {additional_check}"
            example_query = f"SELECT serial_number FROM devices WHERE serial_number ~ '{pattern}' AND {additional_check} LIMIT 5"
        else:
            query = f"SELECT COUNT(*) FROM devices WHERE serial_number ~ '{pattern}'"
            example_query = f"SELECT serial_number FROM devices WHERE serial_number ~ '{pattern}' LIMIT 5"
        
        cursor.execute(query)
        count = cursor.fetchone()[0]
        total_issues += count
        
        if count > 0:
            print_warning(f"{description}: {count} devices")
            
            # Show examples
            cursor.execute(example_query)
            examples = cursor.fetchall()
            for example in examples:
                print(f"    Example: {example[0]}")
        else:
            print_success(f"{description}: 0 devices ✓")
    
    print()
    if total_issues == 0:
        print_success("All serial numbers are valid hardware serials")
        print_info("API validation and client gates are working correctly")
    else:
        print_error(f"Found {total_issues} devices with hostname-like serial numbers")
        print_warning("These should have been rejected by API validation")
        print_warning("Run: python scripts\\manage-db.py --hostnames to clean up")

def cleanup_old_devices(cursor, conn, days=180, dry_run=False, auto_confirm=False):
    """Remove devices not seen in X days"""
    print_header(f"Cleanup: Devices Not Seen in {days} Days")
    
    # Count old devices
    count_query = f"""
    SELECT COUNT(*) FROM devices
    WHERE last_seen < NOW() - INTERVAL '{days} days'
    """
    
    cursor.execute(count_query)
    count = cursor.fetchone()[0]
    
    if count == 0:
        print_success(f"No devices older than {days} days found")
        return
    
    print_info(f"Found {count} devices not seen in {days}+ days")
    
    # List old devices
    list_query = f"""
    SELECT serial_number, name, last_seen,
           EXTRACT(DAY FROM NOW() - last_seen) as days_ago
    FROM devices
    WHERE last_seen < NOW() - INTERVAL '{days} days'
    ORDER BY last_seen ASC
    LIMIT 20
    """
    
    cursor.execute(list_query)
    devices = cursor.fetchall()
    
    print(f"\n{'Serial Number':<25} {'Name':<30} {'Days Ago'}")
    print("-" * 80)
    for serial, name, last_seen, days_ago in devices:
        print(f"{serial:<25} {name:<30} {int(days_ago)}")
    
    if count > 20:
        print(f"\n... and {count - 20} more")
    
    if dry_run:
        print_info("\n[DRY RUN] Would delete these devices")
        return
    
    # Confirm deletion
    print_warning(f"\nAbout to DELETE {count} devices not seen in {days}+ days!")
    
    if not auto_confirm:
        response = input(f"\n{YELLOW}Type 'DELETE' to confirm: {RESET}")
        if response.strip() != 'DELETE':
            print_info("Deletion cancelled")
            return
    
    # Execute deletion
    print_info("\nExecuting deletion...")
    delete_query = f"""
    DELETE FROM devices
    WHERE last_seen < NOW() - INTERVAL '{days} days'
    """
    
    cursor.execute(delete_query)
    deleted_count = cursor.rowcount
    conn.commit()
    
    print_success(f"Deleted {deleted_count} old devices")

def apply_sql_file(cursor, conn, sql_file):
    """Apply a SQL file to the database"""
    print_header(f"Applying SQL: {sql_file}")
    
    path = Path(sql_file)
    if not path.exists():
        print_error(f"File not found: {sql_file}")
        sys.exit(1)
        
    try:
        with open(path, 'r') as f:
            sql = f.read()
            
        print_info(f"Executing SQL from {path.name}...")
        cursor.execute(sql)
        conn.commit()
        print_success(f"Successfully applied {path.name}")
        
    except Exception as e:
        print_error(f"Failed to apply SQL: {e}")
        conn.rollback()
        sys.exit(1)

def show_stats(cursor):
    """Show database statistics"""
    print_header("Database Statistics")
    
    # Total devices
    cursor.execute("SELECT COUNT(*) FROM devices")
    total = cursor.fetchone()[0]
    print_info(f"Total devices: {total}")
    
    # Hostname patterns (matching API validation and client gates)
    # These patterns match what the API rejects and what the client prevents
    cursor.execute("""
        SELECT COUNT(*) FROM devices
        WHERE serial_number ~ '^[A-Z]+-[A-Z]+$'
           OR serial_number ~ '^(DESKTOP|LAPTOP|WORKSTATION|PC)-[A-Z0-9]+$'
           OR serial_number ~ '^WIN-[A-Z0-9]+$'
           OR serial_number ~ '^[A-Z]+-[A-Z]+-[A-Z]+-[0-9]+$'
           OR serial_number ~ '^[A-Z]{4,}-[0-9]{4}$'
           OR serial_number ~ '^[A-Z]{2,}[0-9]{2,}$'
           OR (serial_number ~ '^[A-Z\\-]+$' AND serial_number !~ '[0-9]')
    """)
    hostnames = cursor.fetchone()[0]
    if hostnames > 0:
        print_warning(f"Hostname patterns: {hostnames} (SHOULD BE 0 - API/Client should prevent these!)")
    else:
        print_info(f"Hostname patterns: {hostnames}")
    
    # WIN- prefix
    cursor.execute("SELECT COUNT(*) FROM devices WHERE serial_number LIKE 'WIN-%'")
    win_prefix = cursor.fetchone()[0]
    print_info(f"WIN- prefix: {win_prefix}")
    
    # Duplicates
    cursor.execute("""
        SELECT COUNT(*) FROM (
            SELECT serial_number FROM devices
            GROUP BY serial_number
            HAVING COUNT(*) > 1
        ) t
    """)
    dupes = cursor.fetchone()[0]
    print_info(f"Duplicate serials: {dupes}")
    
    # Last seen distribution
    cursor.execute("""
        SELECT 
            COUNT(CASE WHEN last_seen > NOW() - INTERVAL '1 day' THEN 1 END) as last_24h,
            COUNT(CASE WHEN last_seen > NOW() - INTERVAL '7 days' THEN 1 END) as last_7d,
            COUNT(CASE WHEN last_seen > NOW() - INTERVAL '30 days' THEN 1 END) as last_30d,
            COUNT(CASE WHEN last_seen < NOW() - INTERVAL '180 days' THEN 1 END) as older_180d
        FROM devices
    """)
    stats = cursor.fetchone()
    print_info(f"Last 24 hours: {stats[0]}")
    print_info(f"Last 7 days: {stats[1]}")
    print_info(f"Last 30 days: {stats[2]}")
    print_info(f"Older than 180 days: {stats[3]}")
    
    # Module record counts
    print("\n" + BOLD + "Module Record Counts:" + RESET)
    modules = ['applications', 'displays', 'hardware', 'installs', 'inventory',
               'management', 'network', 'printers', 'profiles', 'security', 'system']
    
    for module in modules:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {module}")
            count = cursor.fetchone()[0]
            print(f"  {module}: {count}")
        except:
            print(f"  {module}: N/A")

def main():
    parser = argparse.ArgumentParser(
        description='ReportMate Database Management Utility',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Apply SQL file
  python manage-db.py --apply schemas/004-performance-indexes.sql

  # Show database statistics
  python manage-db.py --stats

  # Validate serial numbers (check for hostname patterns)
  python manage-db.py --validate

  # Remove hostname-based devices (dry run)
  python manage-db.py --hostnames --dry-run

  # Remove hostname-based devices (execute)
  python manage-db.py --hostnames

  # Remove WIN- prefix devices
  python manage-db.py --win-prefix

  # Remove duplicates
  python manage-db.py --duplicates

  # Remove devices not seen in 180 days
  python manage-db.py --old-devices --days 180

  # Run all cleanups (dry run first!)
  python manage-db.py --all --dry-run

  # Run all cleanups (execute with auto-confirm)
  python manage-db.py --all --yes

Credential Priority (most secure to least):
  1. terraform.tfvars (automatic, secure, recommended)
  2. Environment variable: $env:DB_PASSWORD = 'password'
  3. Command flag: --password 'password' (emergency only, visible in process list!)

Environment Variables:
  DB_SERVER   - Database host (default: reportmate-database.postgres.database.azure.com)
  DB_NAME     - Database name (default: reportmate)
  DB_USER     - Database user (default: reportmate)
  DB_PASSWORD - Database password (fallback if terraform.tfvars not available)
        """
    )
    
    # SQL Application
    parser.add_argument('--apply', type=str,
                       help='Apply a SQL file to the database')

    # Cleanup options
    parser.add_argument('--hostnames', action='store_true',
                       help='Remove devices with hostname patterns (FIRSTNAME-LASTNAME, DESKTOP-, etc.)')
    parser.add_argument('--win-prefix', action='store_true',
                       help='Remove devices with WIN- prefix')
    parser.add_argument('--duplicates', action='store_true',
                       help='Remove duplicate device registrations (keep most recent)')
    parser.add_argument('--old-devices', action='store_true',
                       help='Remove devices not seen in X days')
    parser.add_argument('--all', action='store_true',
                       help='Run all cleanup operations')
    
    # Options
    parser.add_argument('--stats', action='store_true',
                       help='Show database statistics only (no cleanup)')
    parser.add_argument('--validate', action='store_true',
                       help='Validate serial numbers against hostname patterns')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be deleted without deleting')
    parser.add_argument('--yes', '-y', action='store_true',
                       help='Auto-confirm deletions (use with caution!)')
    parser.add_argument('--days', type=int, default=180,
                       help='Days threshold for --old-devices (default: 180)')
    parser.add_argument('--password', type=str,
                       help='Database password (emergency use only, not recommended)')
    
    args = parser.parse_args()
    
    # Show help if no arguments
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)
    
    # Get credentials (automatic from terraform.tfvars)
    creds = get_db_credentials(args)
    
    # Connect to database
    conn, cursor = connect_db(creds)
    
    try:
        # Apply SQL file
        if args.apply:
            apply_sql_file(cursor, conn, args.apply)
            return

        # Show stats
        if args.stats:
            show_stats(cursor)
            return
        
        # Validate serial patterns
        if args.validate:
            validate_serial_patterns(cursor)
            return
        
        # Run cleanups
        if args.all or args.hostnames:
            cleanup_hostnames(cursor, conn, args.dry_run, args.yes)
        
        if args.all or args.win_prefix:
            cleanup_win_prefix(cursor, conn, args.dry_run, args.yes)
        
        if args.all or args.duplicates:
            cleanup_duplicates(cursor, conn, args.dry_run, args.yes)
        
        if args.all or args.old_devices:
            cleanup_old_devices(cursor, conn, args.days, args.dry_run, args.yes)
        
        # Final stats
        print_header("Final Statistics")
        cursor.execute("SELECT COUNT(*) FROM devices")
        total = cursor.fetchone()[0]
        print_success(f"Total devices in database: {total}")
        
    except KeyboardInterrupt:
        print_error("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    main()
