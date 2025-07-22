-- Create devices table with proper schema for ReportMate
-- This is the core table that stores device information

CREATE TABLE IF NOT EXISTS devices (
    id VARCHAR(255) PRIMARY KEY,              -- Uses serial number as primary key
    device_id VARCHAR(255) UNIQUE,            -- UUID from hardware
    name VARCHAR(500),                        -- Computer name/hostname
    serial_number VARCHAR(100) UNIQUE,        -- Hardware serial number (indexed)
    hostname VARCHAR(255),                    -- Network hostname
    model VARCHAR(500),                       -- Hardware model
    os VARCHAR(255),                          -- Full OS string
    os_name VARCHAR(100),                     -- OS name only
    os_version VARCHAR(100),                  -- OS version only
    processor VARCHAR(500),                   -- CPU information
    memory VARCHAR(100),                      -- RAM information
    storage VARCHAR(100),                     -- Storage information
    architecture VARCHAR(50),                 -- Hardware architecture
    last_seen TIMESTAMP WITH TIME ZONE,      -- Last contact time
    status VARCHAR(50) DEFAULT 'unknown',    -- Device status
    ip_address VARCHAR(45),                   -- IP address (IPv4/IPv6)
    mac_address VARCHAR(17),                  -- MAC address
    uptime VARCHAR(100),                      -- System uptime
    client_version VARCHAR(50),               -- ReportMate client version
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create table to store raw osquery data
CREATE TABLE IF NOT EXISTS device_data (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(255) NOT NULL,
    data_type VARCHAR(100) NOT NULL,         -- 'osquery_full', 'hardware', etc.
    raw_data JSONB,                          -- Raw JSON data
    collected_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT device_data_unique UNIQUE(device_id, data_type)
);

-- Create indices for performance
CREATE INDEX IF NOT EXISTS idx_devices_serial_number ON devices(serial_number);
CREATE INDEX IF NOT EXISTS idx_devices_device_id ON devices(device_id);
CREATE INDEX IF NOT EXISTS idx_devices_last_seen ON devices(last_seen);
CREATE INDEX IF NOT EXISTS idx_devices_status ON devices(status);
CREATE INDEX IF NOT EXISTS idx_device_data_device_id ON device_data(device_id);
CREATE INDEX IF NOT EXISTS idx_device_data_type ON device_data(data_type);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to automatically update updated_at
DROP TRIGGER IF EXISTS update_devices_updated_at ON devices;
CREATE TRIGGER update_devices_updated_at
    BEFORE UPDATE ON devices
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
