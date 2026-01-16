-- Peripherals module table for ReportMate
-- Creates table for comprehensive peripheral devices data
-- Categories: USB devices, input devices, audio, Bluetooth, cameras, Thunderbolt, printers, scanners, external storage

-- Peripherals module table
CREATE TABLE IF NOT EXISTS peripherals (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(255) REFERENCES devices(id) ON DELETE CASCADE,
    data JSONB NOT NULL,
    collected_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(device_id)
);

-- Index for faster peripheral lookups
CREATE INDEX IF NOT EXISTS idx_peripherals_device_id ON peripherals(device_id);
CREATE INDEX IF NOT EXISTS idx_peripherals_collected_at ON peripherals(collected_at DESC);

-- GIN index for JSONB queries on peripheral data
CREATE INDEX IF NOT EXISTS idx_peripherals_data_gin ON peripherals USING GIN (data);

-- Comment on the structure
COMMENT ON TABLE peripherals IS 'Comprehensive peripheral devices data collected from clients';
COMMENT ON COLUMN peripherals.data IS 'JSONB containing: usbDevices, inputDevices (keyboards, mice, trackpads, tablets), audioDevices, bluetoothDevices, cameras, thunderboltDevices, printers, scanners, externalStorage, serialPorts';
