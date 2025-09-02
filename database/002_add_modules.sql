-- Module-specific tables for ReportMate
-- Creates tables for each data collection module

-- Applications module
CREATE TABLE IF NOT EXISTS applications (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(255) REFERENCES devices(id) ON DELETE CASCADE,
    data JSONB NOT NULL,
    collected_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(device_id)
);

-- Hardware module  
CREATE TABLE IF NOT EXISTS hardware (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(255) REFERENCES devices(id) ON DELETE CASCADE,
    data JSONB NOT NULL,
    collected_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(device_id)
);

-- Network module
CREATE TABLE IF NOT EXISTS network (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(255) REFERENCES devices(id) ON DELETE CASCADE,
    data JSONB NOT NULL,
    collected_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(device_id)
);

-- Security module
CREATE TABLE IF NOT EXISTS security (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(255) REFERENCES devices(id) ON DELETE CASCADE,
    data JSONB NOT NULL,
    collected_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(device_id)
);

-- System module
CREATE TABLE IF NOT EXISTS system (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(255) REFERENCES devices(id) ON DELETE CASCADE,
    data JSONB NOT NULL,
    collected_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(device_id)
);

-- Installs module
CREATE TABLE IF NOT EXISTS installs (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(255) REFERENCES devices(id) ON DELETE CASCADE,
    data JSONB NOT NULL,
    collected_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(device_id)
);

-- Inventory module
CREATE TABLE IF NOT EXISTS inventory (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(255) REFERENCES devices(id) ON DELETE CASCADE,
    data JSONB NOT NULL,
    collected_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(device_id)
);

-- Management module
CREATE TABLE IF NOT EXISTS management (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(255) REFERENCES devices(id) ON DELETE CASCADE,
    data JSONB NOT NULL,
    collected_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(device_id)
);

-- Displays module
CREATE TABLE IF NOT EXISTS displays (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(255) REFERENCES devices(id) ON DELETE CASCADE,
    data JSONB NOT NULL,
    collected_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(device_id)
);

-- Printers module
CREATE TABLE IF NOT EXISTS printers (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(255) REFERENCES devices(id) ON DELETE CASCADE,
    data JSONB NOT NULL,
    collected_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(device_id)
);

-- Profiles module
CREATE TABLE IF NOT EXISTS profiles (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(255) REFERENCES devices(id) ON DELETE CASCADE,
    data JSONB NOT NULL,
    collected_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(device_id)
);

-- Legacy module_data table for compatibility
CREATE TABLE IF NOT EXISTS module_data (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(255) REFERENCES devices(id) ON DELETE CASCADE,
    module_id VARCHAR(100) NOT NULL,
    data JSONB NOT NULL,
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(device_id, module_id)
);
