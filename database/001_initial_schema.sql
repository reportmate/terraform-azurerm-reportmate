-- Initial schema for ReportMate database
-- Creates core tables for devices, events, and module data

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Devices table (main device registry)
CREATE TABLE IF NOT EXISTS devices (
    id VARCHAR(255) PRIMARY KEY, -- Serial number (primary key)
    device_id UUID, -- Internal UUID
    name VARCHAR(255),
    serial_number VARCHAR(255),
    os VARCHAR(100),
    os_version VARCHAR(100),
    status VARCHAR(50) DEFAULT 'active',
    last_seen TIMESTAMPTZ,
    model VARCHAR(255),
    manufacturer VARCHAR(255),
    client_version VARCHAR(50),
    machine_group_id VARCHAR(255),
    business_unit_id VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Events table (system events and logs)
CREATE TABLE IF NOT EXISTS events (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(255) REFERENCES devices(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL CHECK (event_type IN ('success', 'warning', 'error', 'info')),
    message TEXT NOT NULL,
    details JSONB,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_devices_last_seen ON devices(last_seen);
CREATE INDEX IF NOT EXISTS idx_devices_status ON devices(status);
CREATE INDEX IF NOT EXISTS idx_events_device_id ON events(device_id);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);

-- Add some constraints
ALTER TABLE devices ADD CONSTRAINT IF NOT EXISTS devices_status_check 
    CHECK (status IN ('active', 'inactive', 'offline', 'warning', 'missing'));
