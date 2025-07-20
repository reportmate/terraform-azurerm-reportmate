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

-- ================================
-- PRINTER MODULE TABLES
-- ================================

-- Device printers table
CREATE TABLE IF NOT EXISTS device_printers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id VARCHAR(255) NOT NULL,
    name VARCHAR(500) NOT NULL,
    share_name VARCHAR(500),
    port_name VARCHAR(200),
    driver_name VARCHAR(500),
    location VARCHAR(500),
    comment TEXT,
    status VARCHAR(100),
    printer_status VARCHAR(100),
    is_shared BOOLEAN DEFAULT FALSE,
    is_network BOOLEAN DEFAULT FALSE,
    is_default BOOLEAN DEFAULT FALSE,
    is_online BOOLEAN DEFAULT TRUE,
    server_name VARCHAR(500),
    manufacturer VARCHAR(200),
    model VARCHAR(500),
    device_type VARCHAR(100),
    connection_type VARCHAR(50), -- USB, Network, Parallel, Serial, etc.
    ip_address INET,
    priority INTEGER,
    enable_bidirectional BOOLEAN DEFAULT FALSE,
    keep_printed_jobs BOOLEAN DEFAULT FALSE,
    enable_dev_query BOOLEAN DEFAULT FALSE,
    install_date TIMESTAMP,
    properties JSONB, -- Additional printer properties
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Print drivers table
CREATE TABLE IF NOT EXISTS device_print_drivers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id VARCHAR(255) NOT NULL,
    name VARCHAR(500) NOT NULL,
    version VARCHAR(100),
    environment VARCHAR(100),
    config_file TEXT,
    data_file TEXT,
    driver_path TEXT,
    help_file TEXT,
    monitor_name VARCHAR(200),
    default_data_type VARCHAR(100),
    provider VARCHAR(200),
    driver_version VARCHAR(100),
    driver_date TIMESTAMP,
    is_signed BOOLEAN DEFAULT FALSE,
    dependent_files TEXT[], -- Array of dependent files
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Print ports table
CREATE TABLE IF NOT EXISTS device_print_ports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id VARCHAR(255) NOT NULL,
    name VARCHAR(200) NOT NULL,
    port_type VARCHAR(100),
    description TEXT,
    is_network BOOLEAN DEFAULT FALSE,
    is_local BOOLEAN DEFAULT TRUE,
    timeout_seconds INTEGER,
    transmission_retry INTEGER,
    print_monitor VARCHAR(200),
    configuration JSONB, -- Port configuration details
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Print processors table
CREATE TABLE IF NOT EXISTS device_print_processors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id VARCHAR(255) NOT NULL,
    name VARCHAR(200) NOT NULL,
    environment VARCHAR(100),
    dll_name VARCHAR(200),
    supported_datatypes TEXT[], -- Array of supported data types
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Print jobs table (recent jobs within last 30 days)
CREATE TABLE IF NOT EXISTS device_print_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id VARCHAR(255) NOT NULL,
    printer_name VARCHAR(500) NOT NULL,
    job_id INTEGER,
    document_name TEXT,
    user_name VARCHAR(200),
    status VARCHAR(100),
    submitted_time TIMESTAMP,
    total_pages INTEGER,
    pages_printed INTEGER,
    size_bytes BIGINT,
    priority INTEGER,
    start_time TIMESTAMP,
    until_time TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Print spooler information table
CREATE TABLE IF NOT EXISTS device_print_spooler (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id VARCHAR(255) NOT NULL UNIQUE,
    service_status VARCHAR(50),
    service_start_type VARCHAR(50),
    default_spool_directory TEXT,
    beep_enabled BOOLEAN DEFAULT FALSE,
    net_popup BOOLEAN DEFAULT FALSE,
    log_events BOOLEAN DEFAULT FALSE,
    restart_job_on_pool_error BOOLEAN DEFAULT FALSE,
    restart_job_on_pool_enabled BOOLEAN DEFAULT FALSE,
    port_thread_priority INTEGER,
    scheduler_thread_priority INTEGER,
    total_jobs INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Print policy settings table
CREATE TABLE IF NOT EXISTS device_print_policies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id VARCHAR(255) NOT NULL UNIQUE,
    disable_web_printing BOOLEAN DEFAULT FALSE,
    disable_server_thread BOOLEAN DEFAULT FALSE,
    disable_spooler_open_printers BOOLEAN DEFAULT FALSE,
    spooler_priority INTEGER,
    spooler_max_job_schedule INTEGER,
    enable_logging BOOLEAN DEFAULT FALSE,
    log_level VARCHAR(20),
    restrict_driver_installation BOOLEAN DEFAULT FALSE,
    group_policy_settings JSONB, -- Additional GP settings
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for printer tables
CREATE INDEX IF NOT EXISTS idx_device_printers_device_id ON device_printers(device_id);
CREATE INDEX IF NOT EXISTS idx_device_printers_name ON device_printers(name);
CREATE INDEX IF NOT EXISTS idx_device_printers_is_default ON device_printers(is_default);

CREATE INDEX IF NOT EXISTS idx_device_print_drivers_device_id ON device_print_drivers(device_id);
CREATE INDEX IF NOT EXISTS idx_device_print_drivers_name ON device_print_drivers(name);

CREATE INDEX IF NOT EXISTS idx_device_print_ports_device_id ON device_print_ports(device_id);
CREATE INDEX IF NOT EXISTS idx_device_print_ports_name ON device_print_ports(name);

CREATE INDEX IF NOT EXISTS idx_device_print_processors_device_id ON device_print_processors(device_id);

CREATE INDEX IF NOT EXISTS idx_device_print_jobs_device_id ON device_print_jobs(device_id);
CREATE INDEX IF NOT EXISTS idx_device_print_jobs_printer_name ON device_print_jobs(printer_name);
CREATE INDEX IF NOT EXISTS idx_device_print_jobs_submitted_time ON device_print_jobs(submitted_time);

CREATE INDEX IF NOT EXISTS idx_device_print_spooler_device_id ON device_print_spooler(device_id);

CREATE INDEX IF NOT EXISTS idx_device_print_policies_device_id ON device_print_policies(device_id);

-- Triggers for printer tables
CREATE TRIGGER update_device_printers_updated_at BEFORE UPDATE ON device_printers 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_device_print_drivers_updated_at BEFORE UPDATE ON device_print_drivers 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_device_print_ports_updated_at BEFORE UPDATE ON device_print_ports 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_device_print_processors_updated_at BEFORE UPDATE ON device_print_processors 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_device_print_jobs_updated_at BEFORE UPDATE ON device_print_jobs 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_device_print_spooler_updated_at BEFORE UPDATE ON device_print_spooler 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_device_print_policies_updated_at BEFORE UPDATE ON device_print_policies 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================
-- DISPLAY MODULE TABLES
-- =============================================

-- Display devices table (monitors)
CREATE TABLE IF NOT EXISTS device_displays (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id VARCHAR(255) NOT NULL,
    name VARCHAR(500),
    device_key VARCHAR(500),
    manufacturer VARCHAR(200),
    model VARCHAR(200),
    serial_number VARCHAR(100),
    device_string TEXT,
    
    -- Connection and type
    connection_type VARCHAR(50),
    is_internal BOOLEAN DEFAULT FALSE,
    is_external BOOLEAN DEFAULT FALSE,
    is_primary BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT FALSE,
    is_enabled BOOLEAN DEFAULT FALSE,
    
    -- Physical properties
    diagonal_size_inches DECIMAL(5,2),
    width_mm INTEGER,
    height_mm INTEGER,
    aspect_ratio DECIMAL(5,3),
    
    -- Current settings
    current_width INTEGER,
    current_height INTEGER,
    current_refresh_rate INTEGER,
    current_color_depth INTEGER,
    current_dpi INTEGER,
    current_scaling DECIMAL(5,3),
    current_orientation VARCHAR(50),
    
    -- Capabilities
    max_width INTEGER,
    max_height INTEGER,
    min_width INTEGER,
    min_height INTEGER,
    max_color_depth INTEGER,
    supported_resolutions TEXT, -- JSON array
    supported_refresh_rates TEXT, -- JSON array
    capabilities TEXT, -- JSON array
    
    -- Color and quality
    color_space VARCHAR(50),
    gamma_value DECIMAL(5,3),
    brightness INTEGER,
    contrast INTEGER,
    
    -- Position and layout
    position_x INTEGER,
    position_y INTEGER,
    display_index INTEGER,
    
    -- Technology features
    panel_type VARCHAR(50),
    is_hdr BOOLEAN DEFAULT FALSE,
    is_wide_gamut BOOLEAN DEFAULT FALSE,
    is_adaptive_sync BOOLEAN DEFAULT FALSE,
    is_touch BOOLEAN DEFAULT FALSE,
    
    -- Driver and firmware
    driver_version VARCHAR(100),
    driver_date TIMESTAMP,
    firmware_version VARCHAR(100),
    
    -- EDID information
    edid_manufacturer VARCHAR(100),
    edid_product_code VARCHAR(50),
    edid_week_of_manufacture INTEGER,
    edid_year_of_manufacture INTEGER,
    edid_version VARCHAR(20),
    
    -- Status and health
    status VARCHAR(50),
    health VARCHAR(50),
    last_connected TIMESTAMP,
    usage_hours BIGINT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Display adapters table (graphics cards)
CREATE TABLE IF NOT EXISTS device_display_adapters (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id VARCHAR(255) NOT NULL,
    name VARCHAR(500),
    adapter_device_id VARCHAR(500),
    manufacturer VARCHAR(200),
    chip_type VARCHAR(100),
    dac_type VARCHAR(100),
    memory_size BIGINT,
    driver_version VARCHAR(100),
    driver_date TIMESTAMP,
    bios_version VARCHAR(100),
    connected_displays TEXT, -- JSON array
    supported_modes TEXT, -- JSON array
    max_displays INTEGER,
    is_3d_capable BOOLEAN DEFAULT FALSE,
    is_hardware_accelerated BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Display configuration table (overall settings)
CREATE TABLE IF NOT EXISTS device_display_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id VARCHAR(255) NOT NULL UNIQUE,
    total_displays INTEGER DEFAULT 0,
    active_displays INTEGER DEFAULT 0,
    primary_display VARCHAR(500),
    display_mode VARCHAR(50), -- Extend, Duplicate, Single, etc.
    
    -- Layout settings
    is_extended_desktop BOOLEAN DEFAULT FALSE,
    is_mirrored_desktop BOOLEAN DEFAULT FALSE,
    virtual_desktop_width INTEGER,
    virtual_desktop_height INTEGER,
    
    -- Power management
    display_sleep_timeout INTEGER, -- minutes
    is_power_saving_enabled BOOLEAN DEFAULT FALSE,
    
    -- Accessibility
    is_high_contrast_enabled BOOLEAN DEFAULT FALSE,
    text_scaling DECIMAL(5,3) DEFAULT 1.0,
    is_magnifier_enabled BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Display layout table (positioning)
CREATE TABLE IF NOT EXISTS device_display_layout (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id VARCHAR(255) NOT NULL,
    display_name VARCHAR(500),
    x_position INTEGER,
    y_position INTEGER,
    width INTEGER,
    height INTEGER,
    is_primary BOOLEAN DEFAULT FALSE,
    orientation VARCHAR(50),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Color profiles table
CREATE TABLE IF NOT EXISTS device_color_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id VARCHAR(255) NOT NULL,
    name VARCHAR(500),
    file_path TEXT,
    description TEXT,
    color_space VARCHAR(50),
    device_model VARCHAR(200),
    manufacturer VARCHAR(200),
    is_default BOOLEAN DEFAULT FALSE,
    created_date TIMESTAMP,
    file_size BIGINT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for display tables
CREATE INDEX IF NOT EXISTS idx_device_displays_device_id ON device_displays(device_id);
CREATE INDEX IF NOT EXISTS idx_device_displays_name ON device_displays(name);
CREATE INDEX IF NOT EXISTS idx_device_displays_is_primary ON device_displays(is_primary);
CREATE INDEX IF NOT EXISTS idx_device_displays_is_active ON device_displays(is_active);
CREATE INDEX IF NOT EXISTS idx_device_displays_manufacturer ON device_displays(manufacturer);

CREATE INDEX IF NOT EXISTS idx_device_display_adapters_device_id ON device_display_adapters(device_id);
CREATE INDEX IF NOT EXISTS idx_device_display_adapters_name ON device_display_adapters(name);

CREATE INDEX IF NOT EXISTS idx_device_display_config_device_id ON device_display_config(device_id);

CREATE INDEX IF NOT EXISTS idx_device_display_layout_device_id ON device_display_layout(device_id);
CREATE INDEX IF NOT EXISTS idx_device_display_layout_display_name ON device_display_layout(display_name);

CREATE INDEX IF NOT EXISTS idx_device_color_profiles_device_id ON device_color_profiles(device_id);
CREATE INDEX IF NOT EXISTS idx_device_color_profiles_name ON device_color_profiles(name);
CREATE INDEX IF NOT EXISTS idx_device_color_profiles_is_default ON device_color_profiles(is_default);

-- Triggers for display tables
CREATE TRIGGER update_device_displays_updated_at BEFORE UPDATE ON device_displays 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_device_display_adapters_updated_at BEFORE UPDATE ON device_display_adapters 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_device_display_config_updated_at BEFORE UPDATE ON device_display_config 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_device_display_layout_updated_at BEFORE UPDATE ON device_display_layout 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_device_color_profiles_updated_at BEFORE UPDATE ON device_color_profiles 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
