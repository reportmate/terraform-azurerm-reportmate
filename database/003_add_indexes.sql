-- Performance indexes for ReportMate database
-- Adds indexes for better query performance

-- Module table indexes for device lookups
CREATE INDEX IF NOT EXISTS idx_applications_device_id ON applications(device_id);
CREATE INDEX IF NOT EXISTS idx_applications_collected_at ON applications(collected_at);

CREATE INDEX IF NOT EXISTS idx_hardware_device_id ON hardware(device_id);
CREATE INDEX IF NOT EXISTS idx_hardware_collected_at ON hardware(collected_at);

CREATE INDEX IF NOT EXISTS idx_network_device_id ON network(device_id);
CREATE INDEX IF NOT EXISTS idx_network_collected_at ON network(collected_at);

CREATE INDEX IF NOT EXISTS idx_security_device_id ON security(device_id);
CREATE INDEX IF NOT EXISTS idx_security_collected_at ON security(collected_at);

CREATE INDEX IF NOT EXISTS idx_system_device_id ON system(device_id);
CREATE INDEX IF NOT EXISTS idx_system_collected_at ON system(collected_at);

CREATE INDEX IF NOT EXISTS idx_installs_device_id ON installs(device_id);
CREATE INDEX IF NOT EXISTS idx_installs_collected_at ON installs(collected_at);

CREATE INDEX IF NOT EXISTS idx_inventory_device_id ON inventory(device_id);
CREATE INDEX IF NOT EXISTS idx_inventory_collected_at ON inventory(collected_at);

CREATE INDEX IF NOT EXISTS idx_management_device_id ON management(device_id);
CREATE INDEX IF NOT EXISTS idx_management_collected_at ON management(collected_at);

CREATE INDEX IF NOT EXISTS idx_displays_device_id ON displays(device_id);
CREATE INDEX IF NOT EXISTS idx_displays_collected_at ON displays(collected_at);

CREATE INDEX IF NOT EXISTS idx_printers_device_id ON printers(device_id);
CREATE INDEX IF NOT EXISTS idx_printers_collected_at ON printers(collected_at);

CREATE INDEX IF NOT EXISTS idx_profiles_device_id ON profiles(device_id);
CREATE INDEX IF NOT EXISTS idx_profiles_collected_at ON profiles(collected_at);

-- Legacy module_data indexes
CREATE INDEX IF NOT EXISTS idx_module_data_device_id ON module_data(device_id);
CREATE INDEX IF NOT EXISTS idx_module_data_module_id ON module_data(module_id);
CREATE INDEX IF NOT EXISTS idx_module_data_updated ON module_data(last_updated);

-- JSONB GIN indexes for fast JSON queries (optional, enable if needed)
-- CREATE INDEX IF NOT EXISTS idx_applications_data_gin ON applications USING GIN (data);
-- CREATE INDEX IF NOT EXISTS idx_hardware_data_gin ON hardware USING GIN (data);
-- CREATE INDEX IF NOT EXISTS idx_events_details_gin ON events USING GIN (details);
