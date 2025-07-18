-- ReportMate API Database Schema
-- Schema for modular device data storage

-- Enable UUID extension for primary keys
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Applications table
CREATE TABLE IF NOT EXISTS applications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id VARCHAR(255) NOT NULL,
    name VARCHAR(500) NOT NULL,
    version VARCHAR(100),
    publisher VARCHAR(500),
    install_location TEXT,
    install_date TIMESTAMP,
    size_bytes BIGINT,
    architecture VARCHAR(50),
    source VARCHAR(100) DEFAULT 'unknown',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for device_id lookups
CREATE INDEX IF NOT EXISTS idx_applications_device_id ON applications(device_id);
CREATE INDEX IF NOT EXISTS idx_applications_name ON applications(name);

-- Hardware table
CREATE TABLE IF NOT EXISTS hardware (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id VARCHAR(255) NOT NULL UNIQUE,
    manufacturer VARCHAR(200),
    model VARCHAR(500),
    serial_number VARCHAR(100),
    asset_tag VARCHAR(100),
    processor_name VARCHAR(500),
    processor_cores INTEGER,
    processor_speed_ghz DECIMAL(5,2),
    memory_total_gb DECIMAL(10,2),
    memory_available_gb DECIMAL(10,2),
    storage_total_gb DECIMAL(10,2),
    storage_available_gb DECIMAL(10,2),
    graphics_card TEXT,
    network_adapters TEXT,
    bios_version VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for device_id lookups
CREATE INDEX IF NOT EXISTS idx_hardware_device_id ON hardware(device_id);

-- System information table
CREATE TABLE IF NOT EXISTS system_info (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id VARCHAR(255) NOT NULL UNIQUE,
    os_name VARCHAR(200),
    os_version VARCHAR(100),
    os_build VARCHAR(100),
    os_architecture VARCHAR(50),
    os_edition VARCHAR(100),
    display_version VARCHAR(100),
    install_date TIMESTAMP,
    boot_time TIMESTAMP,
    uptime_seconds BIGINT,
    locale VARCHAR(20),
    timezone VARCHAR(100),
    computer_name VARCHAR(200),
    domain_name VARCHAR(200),
    last_boot_time TIMESTAMP,
    cpu_usage DECIMAL(5,2),
    memory_usage DECIMAL(5,2),
    disk_usage DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for device_id lookups
CREATE INDEX IF NOT EXISTS idx_system_info_device_id ON system_info(device_id);

-- Inventory table
CREATE TABLE IF NOT EXISTS inventory (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id VARCHAR(255) NOT NULL UNIQUE,
    device_name VARCHAR(200),
    serial_number VARCHAR(100),
    uuid VARCHAR(100),
    asset_tag VARCHAR(100),
    allocation VARCHAR(200),
    catalog VARCHAR(200),
    area VARCHAR(200),
    usage_type VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for device_id and serial_number lookups
CREATE INDEX IF NOT EXISTS idx_inventory_device_id ON inventory(device_id);
CREATE INDEX IF NOT EXISTS idx_inventory_serial_number ON inventory(serial_number);

-- Network table
CREATE TABLE IF NOT EXISTS network (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id VARCHAR(255) NOT NULL,
    interface_name VARCHAR(200) NOT NULL,
    interface_type VARCHAR(100),
    mac_address VARCHAR(17),
    ip_address INET,
    subnet_mask INET,
    gateway INET,
    dns_servers TEXT[],
    dhcp_enabled BOOLEAN,
    status VARCHAR(50),
    speed_mbps INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for device_id lookups
CREATE INDEX IF NOT EXISTS idx_network_device_id ON network(device_id);

-- Security table
CREATE TABLE IF NOT EXISTS security (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id VARCHAR(255) NOT NULL UNIQUE,
    antivirus_name VARCHAR(200),
    antivirus_version VARCHAR(100),
    antivirus_enabled BOOLEAN,
    antivirus_updated TIMESTAMP,
    firewall_enabled BOOLEAN,
    tpm_enabled BOOLEAN,
    tpm_version VARCHAR(50),
    encryption_enabled BOOLEAN,
    encryption_method VARCHAR(100),
    secure_boot_enabled BOOLEAN,
    defender_enabled BOOLEAN,
    last_scan_date TIMESTAMP,
    threats_detected INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for device_id lookups
CREATE INDEX IF NOT EXISTS idx_security_device_id ON security(device_id);

-- Management table (MDM/device management info)
CREATE TABLE IF NOT EXISTS management (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id VARCHAR(255) NOT NULL UNIQUE,
    mdm_enrolled BOOLEAN DEFAULT FALSE,
    mdm_server_url VARCHAR(500),
    enrollment_date TIMESTAMP,
    last_checkin TIMESTAMP,
    compliance_status VARCHAR(100),
    ownership_type VARCHAR(50),
    management_agent VARCHAR(200),
    agent_version VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for device_id lookups
CREATE INDEX IF NOT EXISTS idx_management_device_id ON management(device_id);

-- Profiles table (configuration profiles and policies)
CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id VARCHAR(255) NOT NULL,
    profile_name VARCHAR(500) NOT NULL,
    profile_type VARCHAR(100),
    profile_source VARCHAR(100),
    install_date TIMESTAMP,
    status VARCHAR(50),
    description TEXT,
    settings JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for device_id lookups
CREATE INDEX IF NOT EXISTS idx_profiles_device_id ON profiles(device_id);

-- Installs table (managed software installations)
CREATE TABLE IF NOT EXISTS installs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id VARCHAR(255) NOT NULL,
    package_name VARCHAR(500) NOT NULL,
    package_version VARCHAR(100),
    install_status VARCHAR(50),
    install_date TIMESTAMP,
    last_attempt TIMESTAMP,
    attempt_count INTEGER DEFAULT 0,
    error_message TEXT,
    package_source VARCHAR(200),
    installer_type VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for device_id lookups
CREATE INDEX IF NOT EXISTS idx_installs_device_id ON installs(device_id);

-- Events table for audit logging and device activity
CREATE TABLE IF NOT EXISTS device_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id VARCHAR(255) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    event_source VARCHAR(100),
    event_data JSONB,
    severity VARCHAR(20) DEFAULT 'info',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for events
CREATE INDEX IF NOT EXISTS idx_device_events_device_id ON device_events(device_id);
CREATE INDEX IF NOT EXISTS idx_device_events_created_at ON device_events(created_at);
CREATE INDEX IF NOT EXISTS idx_device_events_type ON device_events(event_type);

-- Create a function to update the updated_at timestamp automatically
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for auto-updating updated_at
CREATE TRIGGER update_applications_updated_at BEFORE UPDATE ON applications 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
CREATE TRIGGER update_hardware_updated_at BEFORE UPDATE ON hardware 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
CREATE TRIGGER update_system_info_updated_at BEFORE UPDATE ON system_info 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
CREATE TRIGGER update_inventory_updated_at BEFORE UPDATE ON inventory 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
CREATE TRIGGER update_network_updated_at BEFORE UPDATE ON network 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
CREATE TRIGGER update_security_updated_at BEFORE UPDATE ON security 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
CREATE TRIGGER update_management_updated_at BEFORE UPDATE ON management 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
CREATE TRIGGER update_profiles_updated_at BEFORE UPDATE ON profiles 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
CREATE TRIGGER update_installs_updated_at BEFORE UPDATE ON installs 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
