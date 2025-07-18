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

    -- Add core device identification columns
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

    -- Add network fields - separate IPv4 and IPv6
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'devices' AND column_name = 'ip_address'
    ) THEN
        ALTER TABLE devices ADD COLUMN ip_address VARCHAR(255);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'devices' AND column_name = 'ip_address_v4'
    ) THEN
        ALTER TABLE devices ADD COLUMN ip_address_v4 VARCHAR(45);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'devices' AND column_name = 'ip_address_v6'
    ) THEN
        ALTER TABLE devices ADD COLUMN ip_address_v6 VARCHAR(45);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'devices' AND column_name = 'mac_address'
    ) THEN
        ALTER TABLE devices ADD COLUMN mac_address VARCHAR(255);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'devices' AND column_name = 'mac_address_primary'
    ) THEN
        ALTER TABLE devices ADD COLUMN mac_address_primary VARCHAR(17);
    END IF;

    -- Add status and timing fields
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'devices' AND column_name = 'last_seen'
    ) THEN
        ALTER TABLE devices ADD COLUMN last_seen TIMESTAMPTZ;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'devices' AND column_name = 'status'
    ) THEN
        ALTER TABLE devices ADD COLUMN status VARCHAR(50) DEFAULT 'unknown';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'devices' AND column_name = 'uptime'
    ) THEN
        ALTER TABLE devices ADD COLUMN uptime VARCHAR(255);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'devices' AND column_name = 'location'
    ) THEN
        ALTER TABLE devices ADD COLUMN location VARCHAR(255);
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

    -- Add basic hardware fields
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'devices' AND column_name = 'processor'
    ) THEN
        ALTER TABLE devices ADD COLUMN processor VARCHAR(255);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'devices' AND column_name = 'memory'
    ) THEN
        ALTER TABLE devices ADD COLUMN memory VARCHAR(255);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'devices' AND column_name = 'storage'
    ) THEN
        ALTER TABLE devices ADD COLUMN storage VARCHAR(255);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'devices' AND column_name = 'architecture'
    ) THEN
        ALTER TABLE devices ADD COLUMN architecture VARCHAR(255);
    END IF;

    -- Add system performance metrics
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'devices' AND column_name = 'disk_utilization'
    ) THEN
        ALTER TABLE devices ADD COLUMN disk_utilization INTEGER;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'devices' AND column_name = 'memory_utilization'
    ) THEN
        ALTER TABLE devices ADD COLUMN memory_utilization INTEGER;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'devices' AND column_name = 'cpu_utilization'
    ) THEN
        ALTER TABLE devices ADD COLUMN cpu_utilization INTEGER;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'devices' AND column_name = 'temperature'
    ) THEN
        ALTER TABLE devices ADD COLUMN temperature INTEGER;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'devices' AND column_name = 'battery_level'
    ) THEN
        ALTER TABLE devices ADD COLUMN battery_level INTEGER;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'devices' AND column_name = 'boot_time'
    ) THEN
        ALTER TABLE devices ADD COLUMN boot_time TIMESTAMPTZ;
    END IF;

    -- Add timestamp fields
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'devices' AND column_name = 'created_at'
    ) THEN
        ALTER TABLE devices ADD COLUMN created_at TIMESTAMPTZ DEFAULT NOW();
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'devices' AND column_name = 'updated_at'
    ) THEN
        ALTER TABLE devices ADD COLUMN updated_at TIMESTAMPTZ DEFAULT NOW();
    END IF;
END $$;

-- Create indices for devices table
CREATE INDEX IF NOT EXISTS idx_devices_machine_group_id ON devices(machine_group_id);
CREATE INDEX IF NOT EXISTS idx_devices_serial_number ON devices(serial_number);
CREATE INDEX IF NOT EXISTS idx_devices_asset_tag ON devices(asset_tag);
CREATE INDEX IF NOT EXISTS idx_devices_last_seen ON devices(last_seen);
CREATE INDEX IF NOT EXISTS idx_devices_status ON devices(status);
CREATE INDEX IF NOT EXISTS idx_devices_location ON devices(location);
CREATE INDEX IF NOT EXISTS idx_devices_os ON devices(os);
CREATE INDEX IF NOT EXISTS idx_devices_ip_address_v4 ON devices(ip_address_v4);
CREATE INDEX IF NOT EXISTS idx_devices_ip_address_v6 ON devices(ip_address_v6);
CREATE INDEX IF NOT EXISTS idx_devices_mac_address_primary ON devices(mac_address_primary);
CREATE INDEX IF NOT EXISTS idx_devices_architecture ON devices(architecture);
CREATE INDEX IF NOT EXISTS idx_devices_processor ON devices(processor);

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

-- MDM Information table
CREATE TABLE IF NOT EXISTS mdm_info (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(255) UNIQUE NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    enrolled BOOLEAN NOT NULL DEFAULT FALSE,
    enrolled_via_dep BOOLEAN NOT NULL DEFAULT FALSE,
    server_url VARCHAR(500),
    user_approved BOOLEAN NOT NULL DEFAULT FALSE,
    organization VARCHAR(255),
    department VARCHAR(255),
    enrollment_date TIMESTAMPTZ,
    last_checkin TIMESTAMPTZ,
    mdm_vendor VARCHAR(255),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Fix any existing NULL values in mdm_info table
UPDATE mdm_info SET enrolled_via_dep = FALSE WHERE enrolled_via_dep IS NULL;
UPDATE mdm_info SET enrolled = FALSE WHERE enrolled IS NULL;
UPDATE mdm_info SET user_approved = FALSE WHERE user_approved IS NULL;

-- Security Features table
CREATE TABLE IF NOT EXISTS security_features (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(255) NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    feature VARCHAR(100) NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    status VARCHAR(100) NOT NULL,
    value VARCHAR(255),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(device_id, feature)
);

-- Network Interfaces table
CREATE TABLE IF NOT EXISTS network_interfaces (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(255) NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(100) NOT NULL,
    status VARCHAR(100) NOT NULL,
    ip_address VARCHAR(45),
    mac_address VARCHAR(17),
    gateway VARCHAR(45),
    dns JSONB,
    speed VARCHAR(100),
    ssid VARCHAR(255),
    signal_strength INTEGER,
    channel INTEGER,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Device Hardware table
CREATE TABLE IF NOT EXISTS device_hardware (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(255) UNIQUE NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    processor VARCHAR(255),
    processor_speed VARCHAR(100),
    cores INTEGER,
    threads INTEGER,
    memory VARCHAR(100),
    memory_slots VARCHAR(100),
    storage VARCHAR(100),
    storage_type VARCHAR(100),
    graphics VARCHAR(255),
    vram VARCHAR(100),
    architecture VARCHAR(100),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

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
CREATE INDEX IF NOT EXISTS idx_mdm_info_device_id ON mdm_info(device_id);
CREATE INDEX IF NOT EXISTS idx_mdm_info_enrolled ON mdm_info(enrolled);
CREATE INDEX IF NOT EXISTS idx_security_features_device_id ON security_features(device_id);
CREATE INDEX IF NOT EXISTS idx_security_features_feature ON security_features(feature);
CREATE INDEX IF NOT EXISTS idx_network_interfaces_device_id ON network_interfaces(device_id);
CREATE INDEX IF NOT EXISTS idx_network_interfaces_type ON network_interfaces(type);
CREATE INDEX IF NOT EXISTS idx_device_hardware_device_id ON device_hardware(device_id);

-- Insert default business unit and machine group if they don't exist
INSERT INTO business_units (name, description, created_at, updated_at) 
VALUES ('Default', 'Default business unit for unassigned devices', NOW(), NOW())
ON CONFLICT (name) DO NOTHING;

-- Fix any existing NULL values in business_units
UPDATE business_units SET updated_at = NOW() WHERE updated_at IS NULL;

INSERT INTO machine_groups (name, description, passphrase_hash, business_unit_id, created_at, updated_at)
SELECT 'Default Group', 'Default machine group for unassigned devices', 
       encode(sha256('default-passphrase'::bytea), 'hex'), 
       (SELECT id FROM business_units WHERE name = 'Default'),
       NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM machine_groups WHERE name = 'Default Group');

-- Fix any existing NULL values in machine_groups  
UPDATE machine_groups SET updated_at = NOW() WHERE updated_at IS NULL;

-- Update any existing devices without machine_group_id to use the default group
UPDATE devices 
SET machine_group_id = (SELECT id FROM machine_groups WHERE name = 'Default Group')
WHERE machine_group_id IS NULL;

-- Fix any NULL timestamps in devices table
UPDATE devices SET created_at = NOW() WHERE created_at IS NULL;
UPDATE devices SET updated_at = NOW() WHERE updated_at IS NULL;

-- Data migration and cleanup
-- Update IPv4 addresses from ip_address to ip_address_v4
UPDATE devices 
SET ip_address_v4 = ip_address
WHERE ip_address IS NOT NULL 
  AND ip_address LIKE '%\.%\.%\.%' -- Simple IPv4 pattern
  AND ip_address_v4 IS NULL;

-- Update IPv6 addresses from ip_address to ip_address_v6
UPDATE devices 
SET ip_address_v6 = ip_address
WHERE ip_address IS NOT NULL 
  AND ip_address LIKE '%:%' -- Simple IPv6 pattern
  AND ip_address_v6 IS NULL;

-- Update primary MAC addresses
UPDATE devices 
SET mac_address_primary = mac_address
WHERE mac_address IS NOT NULL 
  AND mac_address_primary IS NULL;

-- Clean up architecture field - standardize to arm64 and x64
UPDATE devices 
SET architecture = 'arm64'
WHERE architecture IN ('ARM 64-bit Processor', 'arm64', 'aarch64', 'ARM64');

UPDATE devices 
SET architecture = 'x64'
WHERE architecture IN ('x86_64', 'x64', 'amd64', 'Intel 64', 'x86-64');

-- Clean up processor names - remove "Virtual CPU @" and similar patterns
UPDATE devices 
SET processor = REGEXP_REPLACE(processor, '^Virtual CPU @ ', '', 'i')
WHERE processor LIKE '%Virtual CPU @%';

UPDATE devices 
SET processor = REGEXP_REPLACE(processor, '^Virtual CPU', 'Virtual Processor', 'i')
WHERE processor LIKE '%Virtual CPU%';

-- Commit transaction
COMMIT;

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
