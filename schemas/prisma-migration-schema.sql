-- ReportMate Database Schema Migration Script
-- This script migrates the production database to match the current Prisma schema
-- Run this script against the production database to fix schema mismatches

-- Start transaction to ensure atomicity
BEGIN;

-- Create business_units table if it doesn't exist
CREATE TABLE IF NOT EXISTS business_units (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create machine_groups table if it doesn't exist
CREATE TABLE IF NOT EXISTS machine_groups (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    passphrase_hash VARCHAR(255) NOT NULL,
    business_unit_id INTEGER REFERENCES business_units(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indices for machine_groups
CREATE INDEX IF NOT EXISTS idx_machine_groups_passphrase_hash ON machine_groups(passphrase_hash);
CREATE INDEX IF NOT EXISTS idx_machine_groups_business_unit_id ON machine_groups(business_unit_id);

-- Create business_unit_users table if it doesn't exist
CREATE TABLE IF NOT EXISTS business_unit_users (
    id SERIAL PRIMARY KEY,
    business_unit_id INTEGER NOT NULL REFERENCES business_units(id) ON DELETE CASCADE,
    username VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'user',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(business_unit_id, username)
);

-- Create index for business_unit_users
CREATE INDEX IF NOT EXISTS idx_business_unit_users_username ON business_unit_users(username);

-- Create business_unit_groups table if it doesn't exist
CREATE TABLE IF NOT EXISTS business_unit_groups (
    id SERIAL PRIMARY KEY,
    business_unit_id INTEGER NOT NULL REFERENCES business_units(id) ON DELETE CASCADE,
    group_name VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'user',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(business_unit_id, group_name)
);

-- Create index for business_unit_groups
CREATE INDEX IF NOT EXISTS idx_business_unit_groups_group_name ON business_unit_groups(group_name);

-- Check if devices table exists and add missing columns
DO $$
BEGIN
    -- Add machine_group_id column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'devices' AND column_name = 'machine_group_id'
    ) THEN
        ALTER TABLE devices ADD COLUMN machine_group_id INTEGER REFERENCES machine_groups(id) ON DELETE SET NULL;
    END IF;

    -- Add other missing columns that might be needed
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'devices' AND column_name = 'serial_number'
    ) THEN
        ALTER TABLE devices ADD COLUMN serial_number VARCHAR(255);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'devices' AND column_name = 'asset_tag'
    ) THEN
        ALTER TABLE devices ADD COLUMN asset_tag VARCHAR(255);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'devices' AND column_name = 'ip_address'
    ) THEN
        ALTER TABLE devices ADD COLUMN ip_address VARCHAR(255);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'devices' AND column_name = 'mac_address'
    ) THEN
        ALTER TABLE devices ADD COLUMN mac_address VARCHAR(255);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'devices' AND column_name = 'last_seen'
    ) THEN
        ALTER TABLE devices ADD COLUMN last_seen TIMESTAMPTZ;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'devices' AND column_name = 'total_events'
    ) THEN
        ALTER TABLE devices ADD COLUMN total_events INTEGER DEFAULT 0;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'devices' AND column_name = 'last_event_time'
    ) THEN
        ALTER TABLE devices ADD COLUMN last_event_time TIMESTAMPTZ;
    END IF;
END $$;

-- Create indices for devices table
CREATE INDEX IF NOT EXISTS idx_devices_machine_group_id ON devices(machine_group_id);
CREATE INDEX IF NOT EXISTS idx_devices_serial_number ON devices(serial_number);
CREATE INDEX IF NOT EXISTS idx_devices_last_seen ON devices(last_seen);

-- Ensure events table has required columns and structure
DO $$
BEGIN
    -- Add missing columns to events table if needed
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'events' AND column_name = 'event_type'
    ) THEN
        ALTER TABLE events ADD COLUMN event_type VARCHAR(100);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'events' AND column_name = 'device_id'
    ) THEN
        ALTER TABLE events ADD COLUMN device_id VARCHAR(255) REFERENCES devices(id);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'events' AND column_name = 'data'
    ) THEN
        ALTER TABLE events ADD COLUMN data JSONB;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'events' AND column_name = 'timestamp'
    ) THEN
        ALTER TABLE events ADD COLUMN timestamp TIMESTAMPTZ DEFAULT NOW();
    END IF;
END $$;

-- Create indices for events table
CREATE INDEX IF NOT EXISTS idx_events_device_id ON events(device_id);
CREATE INDEX IF NOT EXISTS idx_events_event_type ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
CREATE INDEX IF NOT EXISTS idx_events_data_gin ON events USING GIN(data);

-- Create normalized data tables for better querying

-- Software table
CREATE TABLE IF NOT EXISTS software (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(255) NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    version VARCHAR(255),
    vendor VARCHAR(255),
    install_date DATE,
    install_location TEXT,
    uninstall_string TEXT,
    identifying_number VARCHAR(255),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(device_id, name, version, identifying_number)
);

-- Hardware table
CREATE TABLE IF NOT EXISTS hardware (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(255) NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    component_type VARCHAR(100) NOT NULL,
    name VARCHAR(255),
    manufacturer VARCHAR(255),
    model VARCHAR(255),
    serial_number VARCHAR(255),
    capacity VARCHAR(100),
    speed VARCHAR(100),
    details JSONB,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(device_id, component_type, name, serial_number)
);

-- System Information table
CREATE TABLE IF NOT EXISTS system_info (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(255) NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    hostname VARCHAR(255),
    computer_name VARCHAR(255),
    domain VARCHAR(255),
    os_version VARCHAR(255),
    os_build VARCHAR(255),
    architecture VARCHAR(50),
    total_physical_memory BIGINT,
    cpu_brand VARCHAR(255),
    cpu_physical_cores INTEGER,
    cpu_logical_cores INTEGER,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(device_id)
);

-- Create indices for performance
CREATE INDEX IF NOT EXISTS idx_software_device_id ON software(device_id);
CREATE INDEX IF NOT EXISTS idx_software_name ON software(name);
CREATE INDEX IF NOT EXISTS idx_hardware_device_id ON hardware(device_id);
CREATE INDEX IF NOT EXISTS idx_hardware_component_type ON hardware(component_type);
CREATE INDEX IF NOT EXISTS idx_system_info_device_id ON system_info(device_id);

-- Insert default business unit and machine group if they don't exist
INSERT INTO business_units (name, description) 
VALUES ('Default', 'Default business unit for unassigned devices')
ON CONFLICT (name) DO NOTHING;

INSERT INTO machine_groups (name, description, passphrase_hash, business_unit_id)
SELECT 'Default Group', 'Default machine group for unassigned devices', 
       encode(sha256('default-passphrase'::bytea), 'hex'), 
       (SELECT id FROM business_units WHERE name = 'Default')
WHERE NOT EXISTS (SELECT 1 FROM machine_groups WHERE name = 'Default Group');

-- Update any existing devices without machine_group_id to use the default group
UPDATE devices 
SET machine_group_id = (SELECT id FROM machine_groups WHERE name = 'Default Group')
WHERE machine_group_id IS NULL;

-- Commit transaction
COMMIT;

-- Add client_version column to devices table if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'devices' AND column_name = 'client_version'
    ) THEN
        ALTER TABLE devices ADD COLUMN client_version VARCHAR(50);
        -- Add comment for documentation
        COMMENT ON COLUMN devices.client_version IS 'Version of the ReportMate client that last sent data for this device';
    END IF;
END $$;

-- Verify the migration
SELECT 'Migration completed successfully' as result;

-- Show table information
SELECT 
    table_name,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns 
WHERE table_name IN ('devices', 'events', 'business_units', 'machine_groups', 'software', 'hardware', 'system_info')
ORDER BY table_name, ordinal_position;
