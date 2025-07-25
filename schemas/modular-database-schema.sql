-- ReportMate Modular Database Schema
-- Clean, simple schema that matches EXACTLY the Windows client JSON output
-- One table per module + metadata (events) table

-- Note: Using gen_random_uuid() instead of uuid-ossp extension for Azure compatibility

-- =============================================================================
-- CORE DEVICE TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS devices (
    id VARCHAR(255) PRIMARY KEY,                 -- Uses serial number as primary key
    device_id VARCHAR(255) UNIQUE NOT NULL,      -- UUID from hardware (unique constraint)
    name VARCHAR(500),                           -- Computer name/hostname
    serial_number VARCHAR(100) UNIQUE NOT NULL,  -- Hardware serial number (must match id)
    hostname VARCHAR(255),                       -- Network hostname
    model VARCHAR(500),                          -- Hardware model
    manufacturer VARCHAR(500),                   -- Device manufacturer
    os VARCHAR(255),                             -- Full OS string
    os_name VARCHAR(100),                        -- OS name only
    os_version VARCHAR(100),                     -- OS version only
    processor VARCHAR(500),                      -- CPU information
    memory VARCHAR(100),                         -- RAM information
    storage VARCHAR(100),                        -- Storage information
    graphics VARCHAR(500),                       -- Graphics information
    architecture VARCHAR(50),                    -- Hardware architecture
    last_seen TIMESTAMP WITH TIME ZONE,         -- Last contact time
    status VARCHAR(50) DEFAULT 'online',        -- Device status
    ip_address_v4 VARCHAR(45),                  -- IPv4 address
    ip_address_v6 VARCHAR(45),                  -- IPv6 address  
    mac_address_primary VARCHAR(17),            -- Primary MAC address
    uptime VARCHAR(100),                        -- System uptime
    client_version VARCHAR(50),                 -- ReportMate client version
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Ensure serial_number and device_id pair is unique (your requirement)
    CONSTRAINT unique_serial_device_pair UNIQUE (serial_number, device_id)
);

-- =============================================================================
-- EVENTS TABLE (from event.json metadata array)
-- =============================================================================

CREATE TABLE IF NOT EXISTS events (
    id SERIAL PRIMARY KEY,                      -- Using SERIAL instead of UUID for Azure compatibility
    device_id VARCHAR(255) NOT NULL,           -- References devices.id (serial number)
    event_type VARCHAR(20) NOT NULL CHECK (event_type IN ('success', 'warning', 'error', 'info', 'system')),
    message TEXT,
    details JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
);

-- =============================================================================
-- MODULE DATA TABLES (one per JSON file from Windows client)
-- =============================================================================

-- applications.json
CREATE TABLE IF NOT EXISTS applications (
    id SERIAL PRIMARY KEY,                      -- Using SERIAL instead of UUID for Azure compatibility
    device_id VARCHAR(255) NOT NULL,
    data JSONB NOT NULL,                        -- Raw JSON data from applications.json
    collected_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE,
    CONSTRAINT unique_applications_per_device UNIQUE(device_id)
);

-- displays.json  
CREATE TABLE IF NOT EXISTS displays (
    id SERIAL PRIMARY KEY,                      -- Using SERIAL instead of UUID for Azure compatibility
    device_id VARCHAR(255) NOT NULL,
    data JSONB NOT NULL,                        -- Raw JSON data from displays.json
    collected_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE,
    CONSTRAINT unique_displays_per_device UNIQUE(device_id)
);

-- hardware.json
CREATE TABLE IF NOT EXISTS hardware (
    id SERIAL PRIMARY KEY,                      -- Using SERIAL instead of UUID for Azure compatibility
    device_id VARCHAR(255) NOT NULL,
    data JSONB NOT NULL,                        -- Raw JSON data from hardware.json
    collected_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE,
    CONSTRAINT unique_hardware_per_device UNIQUE(device_id)
);

-- installs.json
CREATE TABLE IF NOT EXISTS installs (
    id SERIAL PRIMARY KEY,                      -- Using SERIAL instead of UUID for Azure compatibility
    device_id VARCHAR(255) NOT NULL,
    data JSONB NOT NULL,                        -- Raw JSON data from installs.json
    collected_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE,
    CONSTRAINT unique_installs_per_device UNIQUE(device_id)
);

-- inventory.json
CREATE TABLE IF NOT EXISTS inventory (
    id SERIAL PRIMARY KEY,                      -- Using SERIAL instead of UUID for Azure compatibility
    device_id VARCHAR(255) NOT NULL,
    data JSONB NOT NULL,                        -- Raw JSON data from inventory.json
    collected_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE,
    CONSTRAINT unique_inventory_per_device UNIQUE(device_id)
);

-- management.json
CREATE TABLE IF NOT EXISTS management (
    id SERIAL PRIMARY KEY,                      -- Using SERIAL instead of UUID for Azure compatibility
    device_id VARCHAR(255) NOT NULL,
    data JSONB NOT NULL,                        -- Raw JSON data from management.json
    collected_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE,
    CONSTRAINT unique_management_per_device UNIQUE(device_id)
);

-- network.json
CREATE TABLE IF NOT EXISTS network (
    id SERIAL PRIMARY KEY,                      -- Using SERIAL instead of UUID for Azure compatibility
    device_id VARCHAR(255) NOT NULL,
    data JSONB NOT NULL,                        -- Raw JSON data from network.json
    collected_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE,
    CONSTRAINT unique_network_per_device UNIQUE(device_id)
);

-- printers.json
CREATE TABLE IF NOT EXISTS printers (
    id SERIAL PRIMARY KEY,                      -- Using SERIAL instead of UUID for Azure compatibility
    device_id VARCHAR(255) NOT NULL,
    data JSONB NOT NULL,                        -- Raw JSON data from printers.json
    collected_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE,
    CONSTRAINT unique_printers_per_device UNIQUE(device_id)
);

-- profiles.json
CREATE TABLE IF NOT EXISTS profiles (
    id SERIAL PRIMARY KEY,                      -- Using SERIAL instead of UUID for Azure compatibility
    device_id VARCHAR(255) NOT NULL,
    data JSONB NOT NULL,                        -- Raw JSON data from profiles.json
    collected_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE,
    CONSTRAINT unique_profiles_per_device UNIQUE(device_id)
);

-- security.json
CREATE TABLE IF NOT EXISTS security (
    id SERIAL PRIMARY KEY,                      -- Using SERIAL instead of UUID for Azure compatibility
    device_id VARCHAR(255) NOT NULL,
    data JSONB NOT NULL,                        -- Raw JSON data from security.json
    collected_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE,
    CONSTRAINT unique_security_per_device UNIQUE(device_id)
);

-- system.json
CREATE TABLE IF NOT EXISTS system (
    id SERIAL PRIMARY KEY,                      -- Using SERIAL instead of UUID for Azure compatibility
    device_id VARCHAR(255) NOT NULL,
    data JSONB NOT NULL,                        -- Raw JSON data from system.json
    collected_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE,
    CONSTRAINT unique_system_per_device UNIQUE(device_id)
);

-- =============================================================================
-- BUSINESS LOGIC TABLES (ReportMate specific)
-- =============================================================================

CREATE TABLE IF NOT EXISTS business_units (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS machine_groups (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    business_unit_id INTEGER REFERENCES business_units(id),
    passphrase_hash VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS business_unit_users (
    id SERIAL PRIMARY KEY,
    business_unit_id INTEGER NOT NULL REFERENCES business_units(id),
    username VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'viewer',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(business_unit_id, username)
);

CREATE TABLE IF NOT EXISTS business_unit_groups (
    id SERIAL PRIMARY KEY,
    business_unit_id INTEGER NOT NULL REFERENCES business_units(id),
    group_name VARCHAR(255) NOT NULL,
    permissions JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(business_unit_id, group_name)
);

-- =============================================================================
-- INDEXES FOR PERFORMANCE
-- =============================================================================

-- Devices table indexes
CREATE INDEX IF NOT EXISTS idx_devices_device_id ON devices(device_id);
CREATE INDEX IF NOT EXISTS idx_devices_serial_number ON devices(serial_number);
CREATE INDEX IF NOT EXISTS idx_devices_last_seen ON devices(last_seen);
CREATE INDEX IF NOT EXISTS idx_devices_status ON devices(status);
CREATE INDEX IF NOT EXISTS idx_devices_ip_address_v4 ON devices(ip_address_v4);
CREATE INDEX IF NOT EXISTS idx_devices_mac_address_primary ON devices(mac_address_primary);

-- Events table indexes
CREATE INDEX IF NOT EXISTS idx_events_device_id ON events(device_id);
CREATE INDEX IF NOT EXISTS idx_events_event_type ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);

-- Module tables indexes (for JSONB queries)
CREATE INDEX IF NOT EXISTS idx_applications_device_id ON applications(device_id);
CREATE INDEX IF NOT EXISTS idx_applications_data_gin ON applications USING GIN(data);

CREATE INDEX IF NOT EXISTS idx_displays_device_id ON displays(device_id);
CREATE INDEX IF NOT EXISTS idx_displays_data_gin ON displays USING GIN(data);

CREATE INDEX IF NOT EXISTS idx_hardware_device_id ON hardware(device_id);
CREATE INDEX IF NOT EXISTS idx_hardware_data_gin ON hardware USING GIN(data);

CREATE INDEX IF NOT EXISTS idx_installs_device_id ON installs(device_id);
CREATE INDEX IF NOT EXISTS idx_installs_data_gin ON installs USING GIN(data);

CREATE INDEX IF NOT EXISTS idx_inventory_device_id ON inventory(device_id);
CREATE INDEX IF NOT EXISTS idx_inventory_data_gin ON inventory USING GIN(data);

CREATE INDEX IF NOT EXISTS idx_management_device_id ON management(device_id);
CREATE INDEX IF NOT EXISTS idx_management_data_gin ON management USING GIN(data);

CREATE INDEX IF NOT EXISTS idx_network_device_id ON network(device_id);
CREATE INDEX IF NOT EXISTS idx_network_data_gin ON network USING GIN(data);

CREATE INDEX IF NOT EXISTS idx_printers_device_id ON printers(device_id);
CREATE INDEX IF NOT EXISTS idx_printers_data_gin ON printers USING GIN(data);

CREATE INDEX IF NOT EXISTS idx_profiles_device_id ON profiles(device_id);
CREATE INDEX IF NOT EXISTS idx_profiles_data_gin ON profiles USING GIN(data);

CREATE INDEX IF NOT EXISTS idx_security_device_id ON security(device_id);
CREATE INDEX IF NOT EXISTS idx_security_data_gin ON security USING GIN(data);

CREATE INDEX IF NOT EXISTS idx_system_device_id ON system(device_id);
CREATE INDEX IF NOT EXISTS idx_system_data_gin ON system USING GIN(data);

-- Business logic indexes
CREATE INDEX IF NOT EXISTS idx_machine_groups_business_unit_id ON machine_groups(business_unit_id);
CREATE INDEX IF NOT EXISTS idx_business_unit_users_username ON business_unit_users(username);
CREATE INDEX IF NOT EXISTS idx_business_unit_groups_group_name ON business_unit_groups(group_name);

-- =============================================================================
-- TRIGGERS FOR AUTOMATIC TIMESTAMPS
-- =============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add triggers for all tables with updated_at
CREATE TRIGGER update_devices_updated_at BEFORE UPDATE ON devices FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_applications_updated_at BEFORE UPDATE ON applications FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_displays_updated_at BEFORE UPDATE ON displays FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_hardware_updated_at BEFORE UPDATE ON hardware FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_installs_updated_at BEFORE UPDATE ON installs FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_inventory_updated_at BEFORE UPDATE ON inventory FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_management_updated_at BEFORE UPDATE ON management FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_network_updated_at BEFORE UPDATE ON network FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_printers_updated_at BEFORE UPDATE ON printers FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_profiles_updated_at BEFORE UPDATE ON profiles FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_security_updated_at BEFORE UPDATE ON security FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_system_updated_at BEFORE UPDATE ON system FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_business_units_updated_at BEFORE UPDATE ON business_units FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_machine_groups_updated_at BEFORE UPDATE ON machine_groups FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
