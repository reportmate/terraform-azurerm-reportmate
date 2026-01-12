-- Migration: Add platform column to devices table
-- Purpose: Store the client platform (Windows, macOS) sent from clients at collection time
-- Date: 2025-01-XX

-- Add platform column to devices table
ALTER TABLE devices ADD COLUMN IF NOT EXISTS platform VARCHAR(50);

-- Create index for platform filtering
CREATE INDEX IF NOT EXISTS idx_devices_platform ON devices(platform);

-- Update existing devices with inferred platform based on OS name
UPDATE devices 
SET platform = CASE
    WHEN LOWER(os_name) LIKE '%windows%' OR LOWER(os) LIKE '%windows%' THEN 'Windows'
    WHEN LOWER(os_name) LIKE '%mac%' OR LOWER(os) LIKE '%mac%' OR LOWER(os_name) LIKE '%darwin%' THEN 'macOS'
    ELSE 'Unknown'
END
WHERE platform IS NULL;

-- Add comment for documentation
COMMENT ON COLUMN devices.platform IS 'Operating system platform (Windows, macOS) sent from client at collection time';
