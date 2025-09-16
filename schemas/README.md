# ReportMate Database Schemas

This directory contains all production database schemas and migration files for ReportMate.

## File Organization

### Main Schema Files
- `modular-database-schema.sql` - **Primary production schema** - Complete schema that matches Windows client JSON output exactly
- `prisma-migration-schema.sql` - Prisma-compatible migration schema with business units and normalized structure

### Migration Files (named with 'migration' suffix)
- `001-initial-migration.sql` - Initial core tables (devices, events)  
- `002-modules-migration.sql` - Module-specific tables (applications, hardware, etc.)
- `003-indexes-migration.sql` - Performance indexes
- `client-version-migration.sql` - Client version tracking fields

### Scripts
- `run-migrations.ps1` - Execute all migration files in order

## Architecture

ReportMate uses a **modular database architecture** where:
- Each Windows client JSON module gets its own table
- One table per module: `applications`, `hardware`, `installs`, etc.
- Data stored as JSONB for flexibility
- Simple, clean structure matching client output

## Usage

### Fresh Database Setup
```powershell
# Use the complete schema for new installations
psql $DATABASE_URL -f modular-database-schema.sql
```

### Incremental Migrations
```powershell
# Run sequential migrations for existing databases
.\run-migrations.ps1
```

### Production Deployment
The primary schema file (`modular-database-schema.sql`) is the canonical source of truth and should be used for:
- New infrastructure provisioning
- Production deployments
- Reference documentation

## File Naming Convention
- **Schema files**: Descriptive names (e.g., `modular-database-schema.sql`)
- **Migration files**: Include 'migration' in filename (e.g., `001-initial-migration.sql`)
- **Scripts**: Action-oriented names (e.g., `run-migrations.ps1`)

This organization ensures all database-related production files are centralized and properly versioned.