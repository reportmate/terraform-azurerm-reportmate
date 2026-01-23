-- Migration: Add identity table for user accounts, groups, sessions, login history
-- Run: psql "$DATABASE_URL" -f add_identity_table.sql

-- identity.json (User accounts, groups, sessions, login history, BTMDB health)
CREATE TABLE IF NOT EXISTS identity (
    id SERIAL PRIMARY KEY,                      -- Using SERIAL instead of UUID for Azure compatibility
    device_id VARCHAR(255) NOT NULL,
    data JSONB NOT NULL,                        -- Raw JSON data from identity collection
    collected_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE,
    CONSTRAINT unique_identity_per_device UNIQUE(device_id)
);

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_identity_device_id ON identity(device_id);
CREATE INDEX IF NOT EXISTS idx_identity_collected_at ON identity(collected_at DESC);

-- Trigger for updated_at
CREATE OR REPLACE FUNCTION update_identity_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_identity_timestamp ON identity;
CREATE TRIGGER update_identity_timestamp
    BEFORE UPDATE ON identity
    FOR EACH ROW
    EXECUTE FUNCTION update_identity_updated_at();

-- Verify the table was created
SELECT 'identity table created successfully' AS status WHERE EXISTS (
    SELECT FROM pg_tables WHERE tablename = 'identity'
);
